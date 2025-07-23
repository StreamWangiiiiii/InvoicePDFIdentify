import os
import requests #发送 HTTP 请求，与网页或 API 进行交互
import openpyxl #用于读写 Excel 文件（.xlsx、.xlsm 格式）的库。
from datetime import datetime

import mysql.connector
from mysql.connector import Error
from mysql.connector.cursor import MySQLCursor

# 配置区
API_KEY = "apikey"
DIFY_SERVER = "http://localhost/v1"
DIR_PATH = "/Users/streamwang/Downloads/invoice"
USER = "StreamWang"
# 结果文件名加时间后缀
RESULT_FILE = f"result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"


# 数据库连接配置（MySQL 专属）
DB_CONFIG = {
    "host": "localhost",
    "database": "Invoice",  # 确保数据库已创建
    "user": "root",         # MySQL 用户名（默认root）
    "password": "pwd",    # MySQL 密码
    "port": 3306,           # MySQL 默认端口
    "ssl_disabled": True    # MySQL 禁用SSL的参数（适配驱动）
}

# 字段名与 Dify 输出保持一致，全部英文简洁
FIELDS = [
    "invoice_title",
    "invoice_code",
    "issue_date",
    "buyer_name",
    "buyer_tax_id",
    "seller_name",
    "seller_tax_id",
    "items",
    "total_amount",
    "total_tax",
    "total_with_tax",
    "total_with_tax_in_words", 
    "remarks",
    "issuer"
]

def upload_file(file_path, api_key):
    # 修正上传URL
    url = f"{DIFY_SERVER}/files/upload"
    headers = {'Authorization': f'Bearer {api_key}'}
    ext = os.path.splitext(file_path)[-1].lower()
    if ext == '.pdf':
        mime = 'application/pdf'
    elif ext == '.png':
        mime = 'image/png'
    elif ext == '.jpg' or ext == '.jpeg':
        mime = 'image/jpeg'
    else:
        print(f"[不支持的文件类型] {file_path}，仅支持PDF、PNG、JPG")
        return None
    
    try:
        with open(file_path, 'rb') as file:
            files = {'file': (os.path.basename(file_path), file, mime)}
            data = {'user': USER}
            response = requests.post(url, headers=headers, files=files, data=data)
        
        if response.status_code == 201:
            print(f"[上传成功] {file_path}")
            resp = response.json()
            return resp.get('id')
        else:
            print(f"[上传失败] {file_path}，状态码: {response.status_code}，返回: {response.text}")
            return None
    except Exception as e:
        print(f"[上传异常] {file_path}，错误: {str(e)}")
        return None

def run_workflow(file_id, api_key):
    if not file_id:
        return False, {}, "文件ID为空"
    
    # 修正工作流URL，添加工作流ID   
    url = f"{DIFY_SERVER}/workflows/run"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # 修改输入参数结构
    data = {
        "inputs": {
            "upload": [{
                "transfer_method": "local_file",
                "upload_file_id": file_id,
                "type": "document"
            }]
        },
        "user": USER,
        "response_mode": "blocking"
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 200:
            resp_json = response.json()
            wf_status = resp_json.get("data", {}).get("status")
            
            if wf_status == "succeeded":
                outputs = resp_json.get("data", {}).get("outputs", {})
                return True, outputs, ""
            else:
                error_info = resp_json.get("data", {}).get("error") or resp_json.get("message")
                return False, {}, error_info
        else:
            return False, {}, f"执行工作流失败，状态码: {response.status_code}，详情: {response.text}"
    except Exception as e:
        return False, {}, f"执行工作流异常: {str(e)}"

def save_to_database(filename, result):
    """将发票数据保存到 MySQL 数据库"""
    conn = None
    try:
        # 1. 连接 MySQL 数据库
        conn = mysql.connector.connect(**DB_CONFIG)
        if conn.is_connected():
            conn.autocommit = False  # 禁用自动提交，使用事务
            cur: MySQLCursor = conn.cursor()  # 指定游标类型（支持批量插入）

            # 2. 插入主表数据（MySQL 不支持 RETURNING，用 LAST_INSERT_ID() 获取自增ID）
            insert_master_sql = """
                INSERT INTO invoice_master 
                (file_name, invoice_title, invoice_code, issue_date, 
                 buyer_name, buyer_tax_id, seller_name, seller_tax_id,
                 total_amount, total_tax, total_with_tax, total_with_tax_in_words,
                 remarks, issuer)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            # 处理日期格式（MySQL 支持 'YYYY-MM-DD' 字符串直接插入 DATE 类型字段）
            issue_date = result.get("issue_date")
            if issue_date and isinstance(issue_date, str):
                # 验证日期格式（可选，增强健壮性）
                from datetime import datetime
                try:
                    datetime.strptime(issue_date, "%Y-%m-%d")  # 格式正确则保留
                except ValueError:
                    issue_date = None  # 格式错误则设为空

            # 处理数值类型（避免 None 导致插入失败）
            def parse_decimal(value):
                if value is None:
                    return 0.0
                if isinstance(value, str):
                    # 移除千位分隔符（如 "1,000.00" → "1000.00"）
                    value = value.replace(",", "")
                return float(value) if value != "" else 0.0

            # 主表数据（顺序与 SQL 字段对应）
            master_data = (
                filename,
                result.get("invoice_title") or "",  # 空值处理为空白字符串
                result.get("invoice_code") or "",
                issue_date,
                result.get("buyer_name") or "",
                result.get("buyer_tax_id") or "",
                result.get("seller_name") or "",
                result.get("seller_tax_id") or "",
                parse_decimal(result.get("total_amount")),
                parse_decimal(result.get("total_tax")),
                parse_decimal(result.get("total_with_tax")),
                result.get("total_with_tax_in_words") or "",
                result.get("remarks") or "",
                result.get("issuer") or ""
            )

            # 3. 插入主表并获取自增 ID（MySQL 用 LAST_INSERT_ID()）
            cur.execute(insert_master_sql, master_data)
            # 获取刚插入的主表 ID（MySQL 专属方法）
            cur.execute("SELECT LAST_INSERT_ID()")
            invoice_id = cur.fetchone()[0]  # 提取自增 ID
            print(f"[主表插入成功] 发票ID: {invoice_id}")

            # 4. 处理商品明细（items 是 JSON 字符串，需先解析为列表）
            items_str = result.get("items") or "[]"
            # 解析 JSON 字符串为 Python 列表（处理 Dify 返回的格式）
            import json
            try:
                items = json.loads(items_str)  # 将 '[{"name": "..."}]' 转为列表
                if not isinstance(items, list):
                    items = []  # 确保是列表类型
            except json.JSONDecodeError:
                print(f"[解析错误] items 格式不正确: {items_str}")
                items = []

            # 5. 插入明细表（批量插入）
            if items:
                insert_items_sql = """
                    INSERT INTO invoice_items 
                    (invoice_id, item_name, specification, unit, quantity, 
                     unit_price, amount, tax_rate, tax_amount)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """

                items_data = []
                for item in items:
                    # 处理税率（可能是字符串如 "3%"，需提取数值）
                    tax_rate_str = item.get("tax_rate") or "0"
                    tax_rate = float(tax_rate_str.replace("%", "")) if "%" in tax_rate_str else parse_decimal(tax_rate_str)

                    item_data = (
                        invoice_id,  # 关联主表 ID
                        item.get("name") or "",
                        item.get("specification") or item.get("model") or "",  # 兼容 model 字段
                        item.get("unit") or "",
                        parse_decimal(item.get("quantity")),
                        parse_decimal(item.get("unit_price")),
                        parse_decimal(item.get("amount")),
                        tax_rate,  # 已处理为数值（如 3.0 而非 "3%"）
                        parse_decimal(item.get("tax_amount"))
                    )
                    items_data.append(item_data)

                # 批量插入明细表（高效处理多条数据）
                for item_data in items_data:
                    cur.execute(insert_items_sql, item_data)
                print(f"[明细表插入成功] 共 {len(items_data)} 条商品记录")

            # 6. 提交事务（所有操作成功后提交）
            conn.commit()
            print(f"[数据库] 所有数据保存成功（发票ID: {invoice_id}）")

    except Error as e:
        # MySQL 专属错误处理
        print(f"[MySQL 错误] {str(e)}")
        if conn:
            conn.rollback()  # 出错时回滚事务
    except Exception as e:
        # 其他通用错误（如 JSON 解析失败）
        print(f"[通用错误] {str(e)}")
        if conn:
            conn.rollback()
    finally:
        # 关闭连接（无论成功失败都需关闭）
        if conn and conn.is_connected():
            cur.close()
            conn.close()
            print("[连接关闭] 数据库操作结束")

def batch_process_InvoicePDF(dir_path, result_file):
    # 确保目录存在
    if not os.path.exists(dir_path):
        print(f"[错误] 目录不存在: {dir_path}")
        return
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["filename"] + FIELDS + ["error"])
    
    for filename in os.listdir(dir_path):
        file_path = os.path.join(dir_path, filename)
        
        # 支持PDF、PNG、JPG
        if not os.path.isfile(file_path) or not filename.lower().endswith(('.pdf', '.png', '.jpg', '.jpeg')):
            continue
            
        print(f"\n处理文件: {file_path}")
        
        file_id = upload_file(file_path, API_KEY)
        if not file_id:
            ws.append([filename] + ["" for _ in FIELDS] + ["上传失败"])
            continue
            
        success, outputs, error_info = run_workflow(file_id, API_KEY)
        print(f"输出结果 for {filename}: {outputs}")  # 调试信息
        
        if success:
            # 检查结果结构是否符合预期
            result = outputs.get("result", {})
            print(f"解析结果 for {filename}: {result}")  # 调试信息
            
            # 保存到excel，确保字段存在，避免Excel中出现None
            row = [filename] + [str(result.get(field, "")) for field in FIELDS] + [""]
            #保存到数据库
            save_to_database(filename, result)

        else:
            row = [filename] + ["" for _ in FIELDS] + [error_info]
            print(f"[保存失败]，错误: {error_info}")
            
        ws.append(row)
    
    # 保存Excel文件
    try:
        wb.save(result_file)
        print(f"\n所有结果已写入 {result_file}")
    except Exception as e:
        print(f"[保存失败] 无法写入文件 {result_file}，错误: {str(e)}")




if __name__ == "__main__":
    batch_process_InvoicePDF(DIR_PATH, RESULT_FILE)
