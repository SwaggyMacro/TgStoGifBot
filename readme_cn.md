<p align="center">
    <img src="./images/img_3.gif" width="256px">
</p>
<p align="center">
    <img src="https://img.shields.io/badge/Python-3.11-blue">
    <a href="readme.md"><img src="https://img.shields.io/badge/Lang-English-red"></a>
    <a href="//julym.com/"><img src="https://img.shields.io/badge/Site-julym.com-pink"></a>
    <img src="https://img.shields.io/badge/version-1.0.0-yellow">
    <a href="//github.com/SwaggyMacro/TgStoGifBot"><img src="https://img.shields.io/badge/Repo-TgStoGifBot-green"></a>
</p>

### 📝 系统需求
---
安装运行时依赖。确保它们的路径在PATH变量中：

- **[gifski](https://gif.ski)** 如果你想转换为GIF
- **[ffmpeg](https://ffmpeg.org)** 如果你想转换为APNG
- **[img2webp](https://developers.google.com/speed/webp/docs/img2webp)** 如果你想转换为WEBP

gifski是转换为GIF所唯一需要的依赖，此仓库中只需`仅限gif`，如果你不想转换为APNG或WEBP，你可以忽略其他的。

- gifski
    - Ubuntu: 使用下列命令通过三种不同方式安装gifski：
      ```bash
      brew install gifski
      ```
      ```bash
      sudo snap install gifski
      ```
      ```bash
      cargo install gifski
      ```
    - Windows: 从[gifski官网](https://gif.ski/)下载安装程序。
    - 你可能需要安装[GTk3](https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases)
      运行时以确保lottie在windows下正常工作（需要重新启动）。

### 🖥️ 如何使用
---

#### 0. 你可能需要`执行、读、写`脚本的权限

```bash
chmod +777 ./TgStoGif -R
```

#### 1. 创建一个机器人并从Telegram请求API
- 通过[BotFather](https://t.me/BotFather)创建一个机器人。
    - 复制机器人令牌并保存以备后用。
    - 这里有一个如何创建机器人的[指南](https://core.telegram.org/bots#6-botfather)。
- 登陆[Telegram API](https://my.telegram.org/auth)。
- 点击`API development tools`链接。
- 将出现一个`Create new application`窗口。填写你的应用详情。无需输入任何URL，
  目前只有前两个字段（应用标题和简称）可以稍后更改。
- 点击最后的`Create application`。
- 复制`api_id`、`api_hash`、`bot_token`(来自`@BotFather`)并将它们粘贴在`config.json`文件中。

#### 2. 安装所需的依赖

- 使用以下命令安装所需的依赖：

```bash
pip install -r requirements.txt
```
#### 3. 配置config.json文件
- 将`config.json.example`文件复制为`config.json`并填写所需字段。
```json
{
  "bot_name": "你的机器人名字",
  "api_id": "你的api_id",
  "api_hash": "你的api_hash",
  "bot_token": "你的机器人令牌",
  "proxy": {
    "status": "False", // "True" 如果你想使用代理， "False" 如果你不想使用代理，并填写下面的代理详情，记得删掉这条注释。
    "scheme": "http",
    "hostname": "你的代理主机名",
    "port": "你的代理端口"
  }
}
```
#### 4. 运行脚本

- 使用以下命令运行脚本:
```bash
python main.py
```

示例，你可以使用以下表情包链接来测试机器人：
```
/sets https://t.me/addstickers/PeopleMemes 256x256x100
```
`256x256x100`是gif的大小和质量，你可以将其更改为任何你想要的大小。
如果你没有提供大小和质量，默认是原始大小和质量100。

#### 5. 与机器人对话
- 发送表情给机器人，它会把它转换成gif然后发回给你。
- 发送一个表情包链接给机器人，它会把该表情包中的所有表情转换成gif，压缩后发送回给你。

### 🖼️屏幕截图
---
![截图](./images/img.png)
![截图](./images/img_1.png)
![截图](./images/img_2.png)
![截图](./images/img_4.png)

### 🔗 相关仓库
---
- [lottie-converter](https://github.com/ed-asriyan/lottie-converter) - 将Lottie动画转换成GIF，APNG，和WebP格式。
- [lottie](https://gitlab.com/mattbas/python-lottie) - 在Web、Android和iOS上以及React Native上原生渲染After Effects动画。
- [pyrogram](https://github.com/pyrogram/pyrogram) - 纯Python编写的Telegram MTProto API客户端库和框架，适用于用户和机器人。
- [gifski](https://github.com/ImageOptim/gifski) - GIF编码器。
- [ffmpeg](https://github.com/FFmpeg/FFmpeg) - 一个完整的跨平台解决方案，用于录制、转换和流式传输音频和视频。
