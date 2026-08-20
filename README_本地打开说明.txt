本地打开方法

方法1（推荐）：
双击 start_local_server.bat
浏览器会打开：
http://127.0.0.1:8000

这样网页可以正常读取 data/data.json。

方法2：
直接双击 index.html。
新版会自动使用网页内嵌的备用数据，不再因为 file:// 的 fetch 限制而完全空白。

注意：
1. 首次下载包里的 data.json 是初始化/备用数据。
2. 真正每日行情需要运行 scripts/update_data.py，或上传 GitHub 后由 GitHub Actions 每个工作日自动更新。
3. 如果 ECharts CDN 无法访问，网页会退化成简化显示；联网或 GitHub Pages 环境下可显示完整交互图表。
