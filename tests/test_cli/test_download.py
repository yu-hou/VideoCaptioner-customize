from argparse import Namespace

from videocaptioner.cli import exit_codes as EXIT
from videocaptioner.cli.commands import download
from videocaptioner.core.utils.wechat_channels import WechatChannelsError


class FakeWechatClient:
    def download(self, url, out_dir, progress=None):
        raise WechatChannelsError(
            "尚未配置腾讯元宝 Cookie。请打开“设置 → 视频号 Cookie”，"
            "登录腾讯元宝后点击“读取 Cookie”。"
        )


def test_wechat_download_missing_cookie_prints_hint(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(download, "WechatChannelsClient", FakeWechatClient)
    args = Namespace(url="https://weixin.qq.com/sph/AtBrYj8dQb", output=str(tmp_path), quiet=True)

    result = download.run(args, {})

    captured = capsys.readouterr()
    assert result == EXIT.RUNTIME_ERROR
    assert "腾讯元宝 Cookie" in captured.err
    assert "设置 → 视频号 Cookie" in captured.err
