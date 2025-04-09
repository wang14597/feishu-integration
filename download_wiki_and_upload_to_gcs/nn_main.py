import csv
import json
import requests

import lark_oapi as lark
from lark_oapi.api.auth.v3 import InternalTenantAccessTokenRequest, InternalTenantAccessTokenRequestBody, \
    InternalTenantAccessTokenResponse
from lark_oapi.api.sheets.v3 import QuerySpreadsheetSheetRequest, QuerySpreadsheetSheetResponse

from download_wiki_and_upload_to_gcs.client import create_lark_client
from download_wiki_and_upload_to_gcs.conf import AUTH_INFO


def get_sheet(client, file_token):
    request: QuerySpreadsheetSheetRequest = QuerySpreadsheetSheetRequest.builder() \
        .spreadsheet_token(file_token) \
        .build()

    # 发起请求
    response: QuerySpreadsheetSheetResponse = client.sheets.v3.spreadsheet_sheet.query(request)

    # 处理失败返回
    if not response.success():
        lark.logger.error(
            f"client.sheets.v3.spreadsheet_sheet.query failed, code: {response.code}, msg: {response.msg}, log_id: {response.get_log_id()}, resp: \n{json.dumps(json.loads(response.raw.content), indent=4, ensure_ascii=False)}")
        return
    return lark.JSON.marshal(response.data, indent=4)


def get_tenant_access_token(client):
    request: InternalTenantAccessTokenRequest = InternalTenantAccessTokenRequest.builder() \
        .request_body(InternalTenantAccessTokenRequestBody.builder()
                      .app_id(AUTH_INFO["app_id"]) \
                      .app_secret(AUTH_INFO["app_secret"]) \
                      .build()) \
        .build()

    # 发起请求
    response: InternalTenantAccessTokenResponse = client.auth.v3.tenant_access_token.internal(request)

    # 处理失败返回
    if not response.success():
        lark.logger.error(
            f"client.auth.v3.tenant_access_token.internal failed, code: {response.code}, msg: {response.msg}, log_id: {response.get_log_id()}, resp: \n{json.dumps(json.loads(response.raw.content), indent=4, ensure_ascii=False)}")
        return

    return json.loads(response.raw.content)["tenant_access_token"]


def fetch_sheet_data(tenant_access_token, file_token, sheet_id, condition):
    # 请求的 URL
    url = f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{file_token}/values_batch_get"

    # 查询参数
    params = {
        "ranges": f"{sheet_id}!{condition}",
        "valueRenderOption": "ToString",
        "dateTimeRenderOption": "FormattedString"
    }

    # 请求头
    headers = {
        "Authorization": f"Bearer {tenant_access_token}"
    }

    # 发送 GET 请求
    response = requests.get(url, headers=headers, params=params)

    # 检查响应状态码
    if response.status_code == 200:
        # 返回 JSON 数据
        return response.json()
    else:
        # 如果请求失败，打印错误信息
        print(f"请求失败，状态码：{response.status_code}，响应内容：{response.text}")
        return None


def write_values_to_csv(data, output_file):
    """
    将 values 的内容写入 CSV 文件。

    :param data: 包含 values 数据的字典
    :param output_file: 输出的 CSV 文件名
    """
    try:
        # 确保数据存在，并获取 values
        value_ranges = data.get('data', {}).get('valueRanges', [])
        if not value_ranges:
            print("未找到有效的 values 数据")
            return

        # 获取 values 的内容
        values = value_ranges[0].get('values', [])
        if not values:
            print("values 数据为空")
            return

        # 写入 CSV 文件
        with open(output_file, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            # 写入每一行数据
            writer.writerows(values)

        print(f"数据已成功写入 {output_file}")

    except Exception as e:
        print(f"发生错误：{e}")


def test_nn():
    file = "Vtr4spMdLhYU4ot1tVicEanKnmg"
    client = create_lark_client()
    tenant_access_token = get_tenant_access_token(client)
    sheets = get_sheet(client, file)
    sheets_data = json.loads(sheets)
    max_title_sheet = max(sheets_data["sheets"], key=lambda x: x["title"])
    newest_sheet_id = max_title_sheet["sheet_id"]
    data = fetch_sheet_data(tenant_access_token, file, newest_sheet_id,"A:G")
    write_values_to_csv(data, "output.csv")


if __name__ == '__main__':
    test_nn()
