# Paper Daily

一个面向个人使用的论文日报站点。项目会按预设条件抓取论文、生成静态页面，并可选地把摘要翻译成中文后再发布到 GitHub Pages。

## 摘要翻译

项目默认支持用 DeepSeek 翻译摘要，同时保留英文原文。

页面行为：

- 有翻译结果时，优先显示“中文摘要”，原文折叠到“查看原始摘要”里。
- 没开启翻译或翻译失败时，页面继续显示原始摘要，不会中断生成。

翻译结果会缓存到 `result/translation_cache.json`，相同标题和摘要不会重复请求接口。

## 本地配置

项目启动时会自动读取根目录下的 `.env` 文件，但 `.env` 不应该提交到仓库。

先参考模板创建你自己的本地配置：

```powershell
Copy-Item .env.example .env
```

然后编辑 `.env`：

```env
ENABLE_ABSTRACT_TRANSLATION=true
DEEPSEEK_API_KEY=your-deepseek-api-key
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_API_BASE=https://api.deepseek.com
TRANSLATION_TARGET_LANGUAGE=Simplified Chinese
```

说明：

- `DEEPSEEK_API_KEY` 是必填项，只有它存在时才会真正调用翻译接口。
- `DEEPSEEK_MODEL` 默认为 `deepseek-v4-flash`。
- `DEEPSEEK_API_BASE` 默认为 `https://api.deepseek.com`。
- 如果系统环境变量和 `.env` 同时存在，代码会优先使用系统环境变量，避免覆盖 CI 配置。

## 本地运行

```powershell
uv run python main.py
```

生成后的页面默认在：

- `result/index.html`

测试模板页可以用：

```powershell
uv run python main_test.py
```

## GitHub Actions 配置

推荐做法是：代码继续读取环境变量，但密钥只放在 GitHub Secrets 里，不写进仓库文件。

### 必配 Secret

在仓库的 `Settings > Secrets and variables > Actions` 中添加：

- `DEEPSEEK_API_KEY`

### 可选 Variables

如果你想改默认翻译配置，可以在同一个页面添加 Variables：

- `DEEPSEEK_MODEL`
- `DEEPSEEK_API_BASE`
- `TRANSLATION_TARGET_LANGUAGE`

当前 workflow 已经配置成：

- 有 `DEEPSEEK_API_KEY` 时自动开启翻译
- 没有 `DEEPSEEK_API_KEY` 时自动关闭翻译

这样 GitHub Actions 自动发布时不会把 API key 提交进仓库，也不需要把 key 写死在代码里。
