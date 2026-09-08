# repo-traffic-stats(私有 · 个人流量统计)

**这是一个私有仓库**,只给自己看,不会公开。

它每天自动抓取**你账号下所有仓库**的 GitHub 官方流量(浏览 Views + 克隆 Clones),汇总成一张表格存进仓库——**只更新同一个文件,不会每天生成新文件**。

## 你在哪里看

**两个地方:**

1. **看数据**:打开本仓库根目录的 [`all-traffic.csv`](all-traffic.csv)。这是一个累积表格,每个仓库每天就一行,越攒越多。
2. **看运行情况**:进 **Actions** 标签页,看 `Archive All Traffic` 每次是否跑成功。

## 数据表长什么样(示例)

| repo | date | views | uniques | clones | cloners |
|------|------|------:|--------:|-------:|--------:|
| Nixz0824/AiDocks | 2026-01-01 | 123 | 45 | 12 | 8 |
| Nixz0824/AiDocks | 2026-01-02 | 87 | 30 | 5 | 3 |
| Nixz0824/dsh-sound-cue | 2026-01-01 | 9 | 6 | 1 | 1 |

- `views` = 当天页面浏览量
- `uniques` = 当天独立访客
- `clones` = 当天 `git clone` 次数
- `cloners` = 当天独立克隆人数

## 怎么配置(一次性,约 2 分钟)

唯一的依赖是需要一个 **PAT(专用访问令牌)**,用来读**所有仓库**的流量。GitHub 工作流自带的 `GITHUB_TOKEN` 只对当前这一个仓库有效,读不了别的仓库,所以必须用 PAT。

### 第 1 步:生成一个专用 PAT

1. 打开 <https://github.com/settings/tokens>
2. **Generate new token → Generate new token (classic)**
3. 勾选 **`repo`** 一整项权限即可
4. 设置有效期(建议 90 天或更长,到期后要重新生成并更新 secret)
5. 生成后**复制**那个 `ghp_...` 开头的 token(只在那一刻显示)

### 第 2 步:把 PAT 存成 secret

1. 进入本仓库 → **Settings** → **Secrets and variables** → **Actions**
2. **New repository secret**
3. Name = **`TRAFFIC_PAT`**(严格这个名)
4. Value = 粘贴刚才复制的 token
5. **Add secret**

### 第 3 步:手动跑一次验证

1. 进 **Actions** → 左侧选 **Archive All Traffic** → **Run workflow** → 绿色对勾
2. 跑完后再进仓库根目录,应出现 `all-traffic.csv`,里面是你各仓库的流量。

## 工作流在做什么(简述)

```
每天 06:00 UTC + 手动触发
  → 脚本用 TRAFFIC_PAT 枚举你的所有仓库
  → 逐个抓取 views / clones(每仓库间睡 1 秒 + 限流自动重试)
  → 按 (仓库, 日期) 合并进同一个 all-traffic.csv(取历史最大值,会计入补数据)
  → git add + commit + push(有变化才提交)
```

- 对每个 `(仓库, 日期)` 取**历史最大值**:GitHub 会把某天的数字越算越全,这样能补上延迟的天、也能把低估的升级上去。
- 数据**只保留在仓库里**,即使 GitHub 官方只显示最近 14 天,你也能一直往前查。

## 进阶

- `--owner 用户名`:额外加某个用户/组织的**公开**仓库。
- `--repo owner/repo`:只归档单个仓库。
- 想改抓取的时间点,编辑 `.github/workflows/archive-all-traffic.yml` 里的 `cron`。
- 想换 token:重新生成 PAT 后,把 secret 的值改掉即可。
