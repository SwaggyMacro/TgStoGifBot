<p align="center">
    <img src="./images/img_3.gif" width="256px">

</p>
<p align="center">
    <img src="https://img.shields.io/badge/Python-3.11-blue">
    <a href="//julym.com/"><img src="https://img.shields.io/badge/Site-julym.com-red"></a>
    <img src="https://img.shields.io/badge/version-1.0.0-yellow">
    <a href="//github.com/SwaggyMacro/TgStoGifBot"><img src="https://img.shields.io/badge/Repo-TgStoGifBot-green"></a>
</p>

### 📝 System Requirements
---
Install run-time dependencies. Make sure the path to them present in PATH variable:

- **[gifski](https://gif.ski)** if you want to convert to GIF
- **[ffmpeg](https://ffmpeg.org)** if you want to convert to APNG
- **[img2webp](https://developers.google.com/speed/webp/docs/img2webp)** if you want to convert to WEBP

gifski is the only dependency required to convert to GIF, `gif only` in this repo, you may skip the rest if you don't
want to convert to APNG or WEBP.

- gifski
    - Ubuntu: Install gifski using the following command in three different ways:
      ```bash
      brew install gifski
      ```
      ```bash
      sudo snap install gifski
      ```
      ```bash
      cargo install gifski
      ```
    - Windows: Download the installer from the [gifski website](https://gif.ski/).
    - You may need to install [GTk3](https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases)
      runtime for lottie to work properly in windows(`reboot required`).

### 🖥️ How to use
---

#### 0. You may need permission to execute, read, write the script

```bash
chmod +777 ./TgStoGif -R
```

#### 1. Request the API from Telegram

- Go to [Telegram API](https://my.telegram.org/auth) and log in.
- Click on the `API development tools` link.
- A `Create new application` window will appear. Fill in your application details. There is no need to enter any URL,
  and only the first two fields (App title and Short name) can currently be changed later.
- Click on `Create application` at the end.
- Copy `api_id`, `api_hash`, `bot_token`(from `@BotFather`) and paste them in the `config.json` file.

#### 2. Install the required dependencies

- Install the required dependencies using the following command:

```bash
pip install -r requirements.txt
```

#### 3. Run the script

- Run the script using the following command:
```bash
python main.py
```

#### 4. Talk to the bot
- Send a sticker to the bot, and it will convert it to a gif and send it back to you.
- Send a StickerSet link to the bot, and it will convert all the stickers in the set to gif and zip it then send it back to you.


### 🖼️ScreenShot
---
![Screenshot](./images/img.png)
![Screenshot](./images/img_1.png)
![Screenshot](./images/img_2.png)

### 🔗 Related Repositories
---
- [lottie-converter](https://github.com/ed-asriyan/lottie-converter) - Convert Lottie animations to GIF, APNG, and WebP.
- [lottie](https://gitlab.com/mattbas/python-lottie) - Render After Effects animations natively on Web, Android and iOS,
  and React Native.
- [pyrogram](https://github.com/pyrogram/pyrogram) - Telegram MTProto API Client Library and Framework in Pure Python
  for Users and Bots.
- [gifski](https://github.com/ImageOptim/gifski) - GIF encoder
- [ffmpeg](https://github.com/FFmpeg/FFmpeg) - A complete, cross-platform solution to record, convert and stream audio
  and video.