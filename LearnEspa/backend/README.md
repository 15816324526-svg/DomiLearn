# DomiLearn 本地后端

这个后端负责导入《现代西班牙语1》PDF、在电脑本地调用 Docling 解析整本教材，并保存课文、词表、学习进度和仿写记录。PDF 转换、词表 OCR 与背词判分不调用大模型；课文仿写和模型连接测试会调用你填写的 DeepSeek 官方 API。

## 第一次安装

在 VS Code 打开一个终端，执行：

```powershell
cd D:\LearnEspa\backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m alembic upgrade head
```

Docling 第一次运行时可能需要下载 OCR/版面识别模型。模型下载完成后可以离线解析；教材内容不会被发送给 LLM。

## 每次启动

后端终端：

```powershell
cd D:\LearnEspa\backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

另开一个 VS Code 终端启动前端：

```powershell
cd D:\LearnEspa\frontend
npm.cmd run dev
```

然后访问 `http://127.0.0.1:5173`，进入“教材目录”。选择 PDF 后会立即上传并开始解析，关闭页面不会中止后端任务。

## 数据放在哪里

运行数据都在 `backend/storage`：

- `domilearn.db`：保存教材、解析任务、版本、16 课词表和课文，以及背词和仿写记录。
- `textbooks/modern-spanish-1/originals`：按文件哈希保存原始 PDF，相同文件不会重复保存。
- `textbooks/modern-spanish-1/conversions`：保存每次成功解析的 Markdown、JSON 和报告。
- `logs/jobs`：保存每次解析任务的日志。
- `settings/model-service.json`：保存模型名称、URL 和由 Windows 当前账户加密的 API Key；前端和数据库不会读取明文 Key。
- `reports/imitation-readiness.json`：整本教材的课文、单词和逐句准备检查结果。

已确认的旧版本不会被自动删除。`storage` 是运行数据目录，不应提交到 Git。

## 整本教材自动分类

新上传的 PDF 转换完成后，后端会读取 Docling JSON，识别 16 课的课文，并对词表页运行本机 RapidOCR，按版本、课次和 PDF 页码保存单词。只有 16 课都通过分类检查，版本才会进入“确认使用”。整个导入过程无需 API Key，不消耗模型 Token。

已有的已确认版本可以用保存好的 Docling JSON 补齐整本内容，无须再次转换 PDF：

```powershell
python -m scripts.backfill_book --apply
```

重复运行会保留已有课次、单词和学习记录，不产生重复记录。当前本机已补齐 16 课、32 篇课文；原有第一课进度已保留。检查教材是否能用于逐句仿写：

```powershell
python -m scripts.audit_imitation_readiness
```

## 背单词

先在“教材目录”确认解析成功的版本，再进入“词汇复习”选择章节。程序读取该课词表，依次完成释义选择和中文拼写。每次作答会保存到本地 SQLite；答错或点“暂时不会”会立即显示答案，点击“下一题”后继续。错词会等当前一遍其他词过完再出现，并留给仿写记忆环节。关闭页面后可从原进度继续。

这部分使用普通后端规则判分，不调用大模型。

## 模型设置和课文仿写

在“仪表盘”向下滚动到“设置模型服务”，填写 DeepSeek 官方 Model ID、URL、API Key，点击“填写完毕，点击测试连接”。测试会发一次很短的真实请求，因此可能产生少量模型 Token 费用。只有测试成功才会替换旧设置；“切换服务”会清空三个输入框，旧设置继续生效直到新设置测试成功。请求失败时页面显示 HTTP 状态及原因，点击 × 可关闭。

在“仿写练习”选择课文。系统结合原文、该课错词和历史仿写记录生成本轮完整新情景，然后逐句显示中文题。每句保存草稿再调用模型点评；意思和语法正确但没有沿用教材句式时，可以改写或继续。三次判错后允许手动通过。完成整篇后保存记忆摘要和学习报告；可在“学习报告”查看旧记录并再次仿写。每次生成、点评、报告都会调用模型并消耗 Token。尚未填写真实 API Key 时，这些调用无法实际执行。

## 验证

快速测试（不加载 Docling 模型）：

```powershell
python -m pytest -m "not docling" -q
```

使用教材中的第 10、18、19、24、29 页运行真实 Docling 验证：

```powershell
python -m pytest -m docling tests/integration/test_docling_sample.py -v
```

完整教材为扫描版，CPU 解析可能需要较长时间。程序只显示确实能从 Docling 获得的进度信息，不会伪造百分比。
