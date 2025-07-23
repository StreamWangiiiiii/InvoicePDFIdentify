a = Analysis(
    ['batch_invoicePDF.py'],  # 你的主程序文件
    hiddenimports=[
        'mysql.connector',
        'mysql.connector.cursor',
        'mysql.connector.errorcode',
        'json',
        'openpyxl',
        'requests'
    ],  # 手动指定可能被忽略的依赖
    datas=[],  # 若有静态资源（如模板文件），在此添加（如 ('assets', 'assets')）
    excludes=[],  # 排除不需要的模块（可选）
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='InvoiceProcessor',  # 生成的应用程序名称
    console=True,  # 显示终端窗口（便于查看日志和报错）
    icon=None,  # 可选：添加图标（.icns 格式，macOS专用）
)