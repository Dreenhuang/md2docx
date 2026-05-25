# Markdown批量转DOCX工具 - 开发计划 V2.0 (Web架构版)

## 项目信息

| 项目 | 内容 |
|------|------|
| 技术栈 | Python Flask + python-docx + HTML/CSS/JS |
| 后端端口 | **9473**（已锁定） |
| 前端原型 | gui-design.html（左右分栏布局，1154行） |
| 开发阶段 | V1.0 基础功能 |

## 架构总览

```
浏览器 (http://localhost:9473)
    │
    ▼
┌──────────────────────────────────────┐
│         Flask API Server (:9473)      │
│  ┌──────────┐ ┌──────────────────┐   │
│  │ Static   │ │  API Routes      │   │
│  │ 前端文件  │ │  /api/convert    │   │
│  │ (HTML/   │ │  /api/browse     │   │
│  │  CSS/JS) │ │  /api/files      │   │
│  └──────────┘ │  /api/config     │   │
│              │  /api/progress    │   │
│              └────────┬─────────┘   │
│                       │              │
│  ┌────────────────────▼──────────┐  │
│  │      Core Engine              │  │
│  │  MD Parser → DOCX Generator   │  │
│  │  Header/Footer Formatter      │  │
│  │  Config Manager               │  │
│  └───────────────────────────────┘  │
└──────────────────────────────────────┘
```

---

## Phase 1: 项目初始化与基础架构（预计15分钟）

### Task 1.1: 创建项目目录结构（5分钟）
- 创建后端模块目录：`backend/`、`backend/engine/`、`backend/api/`
- 创建前端目录：`static/css/`、`static/js/`
- 创建配置/日志目录：`config/`、`logs/`、`output/`
- 创建 `requirements.txt`、`.env`、`app.py` 入口文件

### Task 1.2: 安装依赖（5分钟）
- flask>=3.0、python-docx>=1.1.0、markdown>=3.5.0、python-multipart
- 验证所有依赖安装成功

### Task 1.3: 配置管理器实现（5分钟）
- `backend/config.py`: ConfigManager 类
- 默认配置加载、用户配置读写、配置验证
- `default_config.json`: PRD 规定的全部默认参数

**验收标准**: `python app.py` 可启动，访问 localhost:9473 返回首页

---

## Phase 2: 核心转换引擎（预计30分钟）

### Task 2.1: Markdown 解析器（10分钟）
- `backend/engine/md_parser.py`: MarkdownParser 类
- 解析 GFM 语法、提取 YAML Front Matter
- 识别 H1-H6 标题、加粗重点、表格、列表、代码块、图片
- 输出结构化 DocumentNode 中间表示

### Task 2.2: DOCX 生成器（12分钟）
- `backend/engine/docx_generator.py`: DocxGenerator 类
- 基于 python-docx 实现：
  - A4 纸张 / 页边距设置（左20 右20 上16 下16mm）
  - 全局微软雅黑纯黑字体
  - 行距固定值 16 磅、首行缩进 2 字符
  - 标题粗体加大一号、正文常规体小四(12pt)
  - 重点内容粗体加大一号
  - 表格/列表/代码块渲染

### Task 2.3: 页眉页脚生成器（8分钟）
- `backend/engine/header_footer.py`: HeaderFooterGenerator
- 页眉：文档标题居中 / 9pt 微软雅黑 / 纯黑
- 页脚：第X页/共Y页 + 编写日期 / 居中 / 小五号
- 标题提取优先级：YAML > H1 > 文件名

**验收标准**: 单个 .md 文件可转换为格式合规的 .docx 文件

---

## Phase 3: Flask API 服务层（预计20分钟）

### Task 3.1: 文件操作 API（6分钟）
- `POST /api/browse/input` - 选择输入路径（文件/文件夹）
- `POST /api/browse/output` - 选择输出路径
- `GET /api/files` - 获取当前文件列表
- `DELETE /api/files` - 清空文件列表

### Task 3.2: 转换控制 API（8分钟）
- `POST /api/convert/start` - 开始批量转换
- `POST /api/convert/stop` - 停止转换
- `GET /api/convert/progress` - SSE 实时进度推送
- 转换状态管理：内存队列 + 线程安全锁

### Task 3.3: 配置与日志 API（6分钟）
- `GET /api/config` - 获取当前配置
- `PUT /api/config` - 更新配置参数
- `POST /api/config/reset` - 恢复默认
- `GET /api/logs` - 获取日志
- `POST /api/logs/export` - 导出日志为 TXT

**验收标准**: 所有 API 可通过 curl/Postman 测试，返回正确 JSON**

---

## Phase 4: 前端功能实现（预计25分钟）

### Task 4.1: 基于原型增强前端（12分钟）
- 将 gui-design.html 拆分为：`index.html` + `static/css/app.css` + `static/js/app.js`
- 保持 Design Token 系统、SVG 图标、左右分栏布局不变
- 所有 UI 组件保持与设计稿一致

### Task 4.2: API 对接层（8分钟）
- `static/js/api.js`: 封装所有 fetch 调用
- 路径选择对话框（使用 input[type=file] + webkitdirectory）
- 文件列表动态渲染（增删改查）
- 进度条实时更新（SSE 或轮询）

### Task 4.3: 交互逻辑完善（5分钟）
- 格式配置面板折叠/展开
- 按钮状态锁定（转换中禁用）
- 弹窗系统（确认/错误/完成）
- 日志实时滚动显示

**验收标准**: 浏览器中完整 GUI 可操作，点击按钮触发真实 API 调用**

---

## Phase 5: 集成测试与发布（预计15分钟）

### Task 5.1: 端到端功能测试（8分钟）
- 单文件转换测试
- 批量转换（含异常文件）测试
- 格式配置修改→生效验证
- 异常场景友好提示验证

### Task 5.2: 一键启动器 + 文档（7分钟）
- `md2docx启动器.bat`（GBK 编码）
- 自动检测端口、启动 Flask 服务、打开浏览器
- 使用教程文档

**验收标准**: 双击启动器即可完整使用全部功能**

---

## 时间线总览

| Phase | 内容 | 时间 | 关键产出 |
|-------|------|------|----------|
| 1 | 项目初始化+骨架 | 15min | 可启动的 Flask 项目 |
| 2 | 核心转换引擎 | 30min | MD→DOCX 完整流水线 |
| 3 | Flask API 层 | 20min | 8 个 RESTful API |
| 4 | 前端功能实现 | 25min | 完整可交互 GUI |
| 5 | 测试+发布 | 15min | 启动器+文档 |
| **总计** | | **~105min** | **完整可运行项目** |

## 依赖关系

```
Phase 1 (项目骨架)
    ↓
Phase 2 (核心引擎) ←── 可与 Phase 3 并行规划
    ↓                    ↓
Phase 4 (前端实现) ←── Phase 3 (API 层)
    ↓
Phase 5 (集成测试)
```

## 锁定端口配置

| 用途 | 端口 | 协议 |
|------|------|------|
| Flask API + 静态文件服务 | **9473** | HTTP |
