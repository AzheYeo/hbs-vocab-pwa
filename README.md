# 红宝书词源复习 PWA

这是一个面向 iPhone Safari 的离线网页 App。它不是 `.ipa` 安装包，而是一组静态网页文件：

- `index.html`: 应用入口
- `styles.css`: 黑白讲义风样式
- `app.js`: 复习、搜索、错词本逻辑
- `data/vocab.csv`: 红宝书词汇 CSV，应用启动时直接解析，共 6397 个单词
- `manifest.webmanifest`: PWA 安装信息
- `sw.js`: 离线缓存

## 本地预览

在本目录启动一个静态服务器：

```powershell
python -m http.server 5177
```

然后在电脑浏览器打开 `http://127.0.0.1:5177/`。

## iPhone 使用

iPhone 真正像 App 一样安装，建议部署到 HTTPS 地址，例如 GitHub Pages、Netlify、Vercel 或你自己的 HTTPS 服务器。

部署后：

1. 用 iPhone 的 Safari 打开网址。
2. 点击底部分享按钮。
3. 选择“添加到主屏幕”。
4. 从桌面图标打开。

首次加载后，词表会被缓存；学习进度保存在 Safari 本地。
