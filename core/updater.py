import requests
import semver
from packaging.version import parse as parse_version

class Updater:
    def __init__(self, app_context):
        self.app_context = app_context
        self.logger = app_context.shared.logger
        self.current_version = app_context.shared.app_config.get("global_settings", {}).get("app_version", "0.0.0")

    def check_for_updates(self):
        update_settings = self.app_context.shared.app_config.get("update_settings")
        if not update_settings or not update_settings.get("check_on_startup"):
            self.logger.info("更新检查被禁用或未配置。")
            return None

        sources = update_settings.get("sources", [])
        for source in sources:
            if not source.get("enabled"):
                continue

            self.logger.info(f"正在检查更新源: {source.get('type')}...")
            try:
                release_info = self._get_latest_release_info(source)
                if release_info:
                    latest_version = release_info.get("version")
                    if self._is_new_version(latest_version):
                        self.logger.info(f"发现新版本: {latest_version} (当前版本: {self.current_version})")
                        return release_info
                    else:
                        self.logger.info(f"当前已是最新版本。 (版本: {self.current_version})")
                        return None # 找到一个有效的源，并且是最新版，就停止检查
            except Exception as e:
                self.logger.error(f"检查更新源 {source.get('type')} 失败: {e}")
                continue
        
        self.logger.info("所有更新源都检查完毕，未发现新版本。")
        return None

    def _get_latest_release_info(self, source):
        source_type = source.get("type")
        if source_type == "github":
            return self._get_from_github(source)
        elif source_type == "gitee":
            return self._get_from_gitee(source)
        elif source_type == "custom_server":
            return self._get_from_custom_server(source)
        else:
            self.logger.warning(f"未知的更新源类型: {source_type}")
            return None

    def _get_from_github(self, source):
        repo = source.get("repo")
        if not repo:
            return None
        api_url = f"https://api.github.com/repos/{repo}/releases/latest"
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return self._parse_release_info(data)

    def _get_from_gitee(self, source):
        repo = source.get("repo")
        if not repo:
            return None
        api_url = f"https://gitee.com/api/v5/repos/{repo}/releases/latest"
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return self._parse_release_info(data)

    def _get_from_custom_server(self, source):
        url = source.get("url")
        if not url:
            return None
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return self._parse_release_info(data)

    def _parse_release_info(self, data):
        try:
            version = data["tag_name"].lstrip('v')
            download_url = None
            if "assets" in data and data["assets"]:
                # 寻找 .zip 文件
                for asset in data["assets"]:
                    if asset.get("browser_download_url", "").endswith(".zip"):
                        download_url = asset["browser_download_url"]
                        break
                if not download_url: # 如果没有zip，就取第一个
                    download_url = data["assets"][0]["browser_download_url"]

            return {
                "version": version,
                "notes": data.get("body", "没有提供更新日志。"),
                "download_url": download_url,
            }
        except (KeyError, IndexError) as e:
            self.logger.error(f"解析 release 信息失败: {e} - {data}")
            return None

    def _is_new_version(self, latest_version_str):
        try:
            # 使用 packaging.version 来处理复杂的版本号，如 alpha, beta, rc
            latest_v = parse_version(latest_version_str)
            current_v = parse_version(self.current_version)
            return latest_v > current_v
        except Exception as e:
            self.logger.error(f"比较版本号时出错: {e}")
            return False

    def download_update(self, url, save_path, progress_callback=None):
        """
        下载更新文件，并可选地报告进度。
        """
        self.logger.info(f"正在从 {url} 下载更新...")
        try:
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            bytes_downloaded = 0
            
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        bytes_downloaded += len(chunk)
                        if progress_callback and total_size > 0:
                            progress = (bytes_downloaded / total_size) * 100
                            progress_callback(progress)
            
            self.logger.info(f"更新文件已成功下载到: {save_path}")
            return True
        except requests.RequestException as e:
            self.logger.error(f"下载更新失败: {e}")
            return False
        except Exception as e:
            self.logger.exception(f"下载过程中发生未知错误:")
            return False