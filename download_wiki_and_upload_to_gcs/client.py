import lark_oapi as lark

from conf import AUTH_INFO


def create_lark_client():
    client = lark.Client.builder() \
        .app_id(AUTH_INFO["app_id"]) \
        .app_secret(AUTH_INFO["app_secret"]) \
        .log_level(lark.LogLevel.DEBUG) \
        .build()
    return client
