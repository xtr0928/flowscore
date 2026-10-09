# 静态部署指南

本项目是纯静态页面，构建产物只有一个 `index.html`（以及可选的资源文件），不需要 Node.js、不需要任何后端服务。以下提供三种最小可复制的部署方式。

约定：下文所有配置均假设将 `index.html` 放在服务器的 `/var/www/html/`（或对应目录）下，实际路径请自行替换。

---

## 方式一：Nginx

最小可复制的 `server` 块示例（可放入 `/etc/nginx/conf.d/xtr.conf`，或改写进 `nginx.conf` 的 `http` 块内）：

```nginx
server {
    listen       80;
    server_name  example.com;        # 换成你的域名或 IP

    root   /var/www/html;            # index.html 所在目录
    index  index.html;

    charset utf-8;

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

要点：

- `charset utf-8;` 必须保留。本项目页面为 UTF-8 编码，且内置测试用例包含中文文件名/中文文案，缺少该行时部分浏览器会按 Latin-1 解码导致乱码。
- `try_files` 保证了刷新子路径时不出现 404（详见文末"子路径托管"）。

生效命令：

```bash
sudo nginx -t && sudo nginx -s reload
```

---

## 方式二：Apache（httpd）

最小可复制的 VirtualHost（放入 `/etc/httpd/conf.d/xtr.conf` 或 `/etc/apache2/sites-available/xtr.conf`）：

```apache
<VirtualHost *:80>
    ServerName example.com
    DocumentRoot /var/www/html

    <Directory /var/www/html>
        Require all granted
        Options -Indexes
    </Directory>

    AddDefaultCharset UTF-8

    DirectoryIndex index.html
</VirtualHost>
```

要点：

- `AddDefaultCharset UTF-8` 必须保留，作用与 Nginx 的 `charset utf-8;` 相同。
- 如果需要子路径刷新不 404，可开启 rewrite：

```apache
    <IfModule mod_rewrite.c>
        RewriteEngine On
        RewriteCond %{REQUEST_FILENAME} !-f
        RewriteCond %{REQUEST_FILENAME} !-d
        RewriteRule . /index.html [L]
    </IfModule>
```

生效命令：

```bash
# Debian/Ubuntu
sudo a2ensite xtr && sudo systemctl reload apache2
# RHEL/CentOS
sudo systemctl reload httpd
```

---

## 方式三：Python 内置服务器（零配置）

一行命令，适合临时演示、本机联调或内网快速分享：

```bash
python -m http.server 8080
```

在 `index.html` 所在目录执行，然后浏览器打开 `http://localhost:8080/` 即可。

- 需要 Python 3（Python 2 请用 `python2 -m SimpleHTTPServer 8080`，不建议）。
- 该服务器默认按文件系统编码响应，现代浏览器通常能正确识别 UTF-8；若遇到乱码请改用方式一或方式二。

---

## 常见问题

### 1. 中文文件名 / 中文文案乱码

原因：服务器未声明字符集，浏览器按错误编码（通常是 Latin-1 / GBK 兜底）解码。

解决：

- Nginx：确保 `server` 块中有 `charset utf-8;`
- Apache：确保 VirtualHost 中有 `AddDefaultCharset UTF-8`
- `index.html` 本身应以 UTF-8（无 BOM）保存，且 `<head>` 中已有 `<meta charset="utf-8">`
- 引用带中文名的文件时，URL 中的中文应由浏览器自动百分号编码，无需手动转码

### 2. `file://` 与 `http://` 的行为差异

直接双击打开（`file://` 协议）在多数浏览器中也能看页面，但存在差异：

| 行为 | `file://` | `http://` |
| --- | --- | --- |
| 加载本地 JSON / fetch 同目录文件 | 多数浏览器因同源策略拦截（`origin` 为 `null`） | 正常 |
| Cookie / localStorage | 部分浏览器隔离或禁用 | 正常 |
| Service Worker / 部分新版 API | 不可用 | 正常 |
| 相对路径解析 | 依赖文件真实位置，行为不一 | 由服务器路由决定，可控 |

结论：日常预览用 `file://` 勉强可行；凡是涉及 fetch 本地文件、跑 `tests/test.html` 或验证部署效果的，一律用 `http://`（最简单就是方式三）。

### 3. 为什么不需要 Node / 后端？

本项目全部逻辑（Schema 校验、`XTR.graph` API、渲染、测试）都在浏览器端完成：

- 没有任何服务端渲染或接口依赖；
- 管线文档（`pipelineDoc`）由前端直接生成、校验与导出，不需要服务端持久化；
- 构建产物是静态 `index.html`，无需打包或编译步骤。

因此任意能托管静态文件的方案（Nginx、Apache、`python -m http.server`、GitHub Pages、对象存储 + CDN）都可以直接使用，引入 Node 或后端只会增加无谓的运维成本。

### 4. 如何用子路径托管？

例如部署到 `https://example.com/xtr/` 而不是根路径：

1. 把 `index.html` 放到 `/var/www/html/xtr/` 下。
2. 确认页面内引用（如有）使用**相对路径**，如 `./schema/schema.json`，而不是以 `/` 开头的绝对路径——否则请求会落到站点根。
3. Nginx 保持 `try_files $uri $uri/ /index.html;` 不变即可，它天然支持子目录。
4. Apache 子路径刷新 404 时，使用上文 rewrite 片段，并将规则改为 `RewriteRule . /xtr/index.html [L]`。
5. `python -m http.server 8080` 场景：在 `xtr/` 目录内启动命令，访问 `http://localhost:8080/` 即等价于子路径托管。

---

## 部署自查清单

- [ ] `index.html` 以 UTF-8（无 BOM）保存
- [ ] 服务器配置中已声明 UTF-8 字符集（Nginx `charset` / Apache `AddDefaultCharset`）
- [ ] 通过 `http://` 访问（而非 `file://`）验证一遍完整功能
- [ ] 部署后跑一次 `tests/test.html`，确认用例全部通过（M2 之后用例只增不减，若失败优先排查编码与路径问题）
- [ ] 子路径场景下检查所有引用均为相对路径
