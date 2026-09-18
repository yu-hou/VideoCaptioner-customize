"""抖音 Web 接口的请求签名（纯 Python，无 JS 引擎、无浏览器）。

抖音 Web API 现已对视频详情等接口做双重签名保护：

1. ``a_bogus`` —— 由页面 SDK ``bdms.js`` 在 VM 中生成，见 :mod:`abogus`。
   缺失时 detail 接口返回空 ``aweme_detail``，yt-dlp 表现为
   "Fresh cookies (not necessarily logged in) are needed"。
2. ``x-secsdk-web-signature`` —— 由 ``@byted/secsdk-strategy`` 生成，
   ``md5(uifid_timestamp_salt_query)``，见 :mod:`websign`。缺失时返回
   ``403 Blocked by ArgusSecurityPlugin Uifid Not Found``。

两个模块均取自 https://github.com/Evil0ctal/Douyin_TikTok_Download_API
（Apache-2.0），于 2026-09-18 引入，仅修改了 SM3 的导入路径。
"""

from videocaptioner.core.utils.douyin_sign.abogus import ABogus
from videocaptioner.core.utils.douyin_sign.websign import SALT as WEB_SIGN_SALT
from videocaptioner.core.utils.douyin_sign.websign import (
    VERIFY_FP_COOKIE,
    encode_pairs,
    pick_uifid,
    sign,
)

__all__ = [
    "ABogus",
    "VERIFY_FP_COOKIE",
    "WEB_SIGN_SALT",
    "encode_pairs",
    "pick_uifid",
    "sign",
]
