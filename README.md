# repo-traffic-stats · 仓库流量统计

每天自动抓取 **GitHub 官方 Traffic(浏览 Views + 克隆 Clones)** 并归档进 `all-traffic.csv`,再渲染成一个交互看板。

## 📍 直接在线查看(推荐)

👉 **<https://nixz0824.github.io/repo-traffic-stats/>**

点开即是最新看板;页面右上角有「**⟳ 更新数据**」按钮,点击后从公开仓库拉取最新 `all-traffic.csv` 并重建,无需重新下载。

> 本仓库为**公开**仓库(流量数字公开可见)。所有数据只存在一个 `all-traffic.csv` 文件里,每仓库每天一行。

## 🗃 数据(一个文件)

| repo | date | views | uniques | clones | cloners |
|------|------|------:|--------:|-------:|--------:|
| Nixz0824/AiDocks | 2026-01-01 | 123 | 45 | 12 | 8 |

- `views` 浏览人次 · `uniques` 独立访客 · `clones` 克隆次数 · `cloners` 独立克隆者
- 对每个 `(仓库, 日期)` 取**历史最大值**,能补回 GitHub 延迟校正的数据。

## 🎯 看板功能

- **类别**:浏览 / 访客 / 克隆 / 克隆者
- **粒度**:日 / 周 / 月 … **范围**:全部仓库 / 单个仓库
- **时间**:近 7 / 14 / 30 / 90 / 365 天 / 全部
- 顶部 KPI 卡 + 趋势图 + 仓库排名 + 可排序明细表
- 时间范围**相对数据最新一天**计算,什么时候打开都正确。

## ⚙️ 工作原理

`.github/workflows/archive-all-traffic.yml`(每天 06:00 UTC + 手动触发):
1. `scripts/archive_all_traffic.py --all`:用 PAT 枚举所有仓库,逐个抓 views/clones。
2. `scripts/render_dashboard.py`:读 `all-traffic.csv`,生成 `index.html` + `dashboard.html`。
3. 提交回仓库 → GitHub Pages 自动更新在线看板。

> 仓库自带的 `GITHUB_TOKEN` 只能访问本仓库,无法读其他私有仓库的流量,所以需要把**个人访问令牌(`repo` 权限)** 存到仓库 secret `TRAFFIC_PAT`;该 token 绝不写入代码/前端。
