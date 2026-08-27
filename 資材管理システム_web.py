#ここから初期設定
import streamlit as st
#Streamlit本体。入力欄やボタン、画面表示などを作るために使う
import pandas as pd
#スプレッドシートから読み込んだ表データをPythonで扱いやすくする
from streamlit_gsheets import GSheetsConnection
#StreamlitとGoogleスプレッドシートを接続するための機能
from datetime import datetime,date
#入出庫した瞬間の日時を取得
from io import BytesIO
#BytesIO は簡単にいうと、ファイルをPCに保存せず、Pythonの中に一時的に持っておく入れ物
## Excelファイルを一時的にメモリ上へ保存するために使用
SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]#URLを隠す[]の所から持ってくる
from zoneinfo import ZoneInfo#時間（場所）関係
import bcrypt#パスワード関係
#ここから関数

    
#データ保存
def save():#更新後のdataをスプレッドシートへ書き戻す
           # data=data：変更後のdata（表）をスプレッドシートに渡して更新
    conn.update(
        spreadsheet=SHEET_URL,
        data=data)
    
#入出庫履歴保存
def history_save(condition, amount, item_name, stock_typ, current_stock,cancel_situation):
    global history_data
    code_number = data.loc[condition, "資材コード"].iloc[0]
    now = datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%Y/%m/%d %H:%M:%S")#その瞬間の東京の日時がnowに入る　表示方法2026/08/16 16:52:31
    new_history_data = pd.DataFrame([{
        "日時":now,
        "資材コード": code_number,
        "品名": item_name,
        "区分": stock_typ,
        "数量": amount,
        "入出庫後在庫数":current_stock,
        "取消状況":cancel_situation,
        "作業者":st.session_state["login_user"]
        }])

    history_data = pd.concat([history_data, new_history_data], ignore_index=True)

    conn.update(
    spreadsheet=SHEET_URL,
    worksheet="入出庫履歴",
    data=history_data
)

#発注履歴保存
def order_save(condition_name, stock_typ,order_date,delivery_date,order_quantity):
    global order_data
    code_number = data.loc[condition_name, "資材コード"].iloc[0]
    item_name = data.loc[condition_name, "品名"].iloc[0]

    now = datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%Y/%m/%d %H:%M:%S")#その瞬間の日時がnowに入る　表示方法2026/08/16 16:52:31
    new_order_data = pd.DataFrame([{
        "日時":now,
        "資材コード": code_number,
        "品名": item_name,
        "区分": stock_typ,
        "発注日":order_date,
        "納入予定日":delivery_date,
        "発注数量": order_quantity,
        "作業者":st.session_state["login_user"]
        }])

    order_data = pd.concat([order_data, new_order_data], ignore_index=True)

    conn.update(
    spreadsheet=SHEET_URL,
    worksheet="発注履歴",
    data=order_data
)
       
#入出庫
def stock_in_out_form(form_name,header_name,amount_name):#入出庫フォーム用関数
    with st.form(form_name, clear_on_submit=True,enter_to_submit=False):
        st.header(header_name)
        st.write("資材コードもしくは品名を入力してください")
        code=st.text_input("資材コード")
        item=st.text_input("品名")
        amount=st.number_input(amount_name,min_value=1)
        submitted_stock = st.form_submit_button(header_name) 
        return  code,item,amount,submitted_stock

def stock_in_out_check(stock_typ):#入出庫チェック用関数（記録用関数使用）
    if code:
        condition=data["資材コード"]== code
        if not code.isdigit() or len(code)!= 8:
            st.error("資材コードは8桁の数字で入力してください") 
        elif not code in data["資材コード"].values:
            st.error("この資材コードは登録されていません") 
        else:
            if stock_typ=="入庫":
                stock_fluc_save("資材コード","入庫")
            elif stock_typ=="出庫":
                if amount>data.loc[condition,"在庫数"].iloc[0]:
                    st.error("出庫数が在庫数より多いです") 
                else:
                    stock_fluc_save("資材コード","出庫")
                    
                
    elif item:
        condition=data["品名"]== item
        if not item in data["品名"].values:
            st.error("この品名は登録されていません") 
        elif len(data.loc[condition])>1:
            st.error("同じ名前が複数あるため資材コードを入力してください")
            st.dataframe(data.loc[condition,["資材コード","品名"]],hide_index=True)
            #「data.loc で取り出した表を、indexだけ隠して表示する」
        else:
            code_number = data.loc[condition, "資材コード"].iloc[0]#品名に対する資材コード
            if stock_typ=="入庫":
                stock_fluc_save("品名","入庫")
                st.warning(f"資材コードのご確認をお願いします：{code_number}")
            elif stock_typ=="出庫":
                if amount>data.loc[condition,"在庫数"].iloc[0]:
                    st.error("出庫数が在庫数より多いです") 
                else:
                    stock_fluc_save("品名","出庫")
                    st.warning(f"資材コードのご確認をお願いします：{code_number}")
    else:
        st.error("資材コードもしくは品名を入力してください")  

def stock_fluc_save(stock_pattern,stock_typ):#入出庫数記録用関数
    if stock_pattern=="資材コード":
        condition=data["資材コード"]== code
    elif stock_pattern=="品名":
        condition=data["品名"]== item
    if stock_typ=="入庫":
        data.loc[condition,"在庫数"]+=amount
    elif stock_typ=="出庫":
        data.loc[condition,"在庫数"]-=amount
    item_name=data.loc[condition,"品名"].iloc[0]
    current_stock=int(data.loc[condition,"在庫数"].iloc[0])#入出庫後数量
    save()
    history_save(condition, amount, item_name, stock_typ, current_stock,"無")
    st.success(f"{item_name}を{amount}個{stock_typ}しました  \n現在の在庫数：{current_stock}個")
    code_number = data.loc[condition, "資材コード"].iloc[0]
    history_condition = history_data["資材コード"] == code_number
    st.dataframe(history_data.loc[
            history_condition,
            ["資材コード","品名","区分","数量","入出庫後在庫数"]],hide_index=True)

#一覧ソート用関数
def show_stock (button_name,sort_typ_name=None,sort_name=None):
    #button_nameは必須。でも残り2つは必要なときだけ渡してね(引数を省略したら自動的に None が入る)
    if button_name:
        if sort_typ_name is None:
            # 絞り込みなし＝全品目
            st.dataframe(data[[
                "資材コード","品名","型式・寸法","在庫数","最低在庫数","使用会社","形区分"]],
            hide_index=True,
            use_container_width=True)
            #use_container_width=True：画面いっぱいに広げる
        else:
            condition=data[sort_typ_name]==sort_name
            st.write(sort_name)
            st.dataframe(data.loc[
                condition,[
                "資材コード","品名","型式・寸法","在庫数","最低在庫数","使用会社","形区分"]],
                hide_index=True,
                use_container_width=True)
            
#帳簿編集用関数
def create_ledger(ledger_data,search_code_name):
    #【初期設定】
    item_condition=data["資材コード"]==st.session_state[search_code_name]
    # excel_data：完成したExcelデータを入れておく箱
    excel_data = BytesIO()
    # writer：Excelを作ってexcel_dataへ書き込むための窓口
    # with st.form()と同じように、with内がExcelを作成する範囲
    with pd.ExcelWriter(excel_data, engine="xlsxwriter") as writer:
        ledger_data = ledger_data.drop(columns=["資材コード", "品名"])
        # ledger_dataの内容を表としてExcelへ書き込む
        # startrow=6 → Excelの7行目から書き込み
        ledger_data.to_excel(
            writer,
            sheet_name="在庫帳簿",
            index=False,
            startrow=7
        )

        # workbook：writerが作成しているExcelブック全体
        workbook = writer.book

        # worksheet：Excelブックの中の「在庫帳簿」シート
        worksheet = writer.sheets["在庫帳簿"]

        #【書式作成】
        # タイトルに使用する書式を作成（別のシートでも使える）
        title_format = workbook.add_format({
            "bold": True,       # 太字
            "font_size": 16,    # 文字サイズ
            "align": "center",   # 中央揃え
            "border": 1,
            "bg_color":"#D9D9D9"
        })#workbook.add_format:書式セットを作る」機能

        #基本情報（ヘッダー部分）の書式
        info_header_format = workbook.add_format({"bold": True,"border": 1,"bg_color":"#D9D9D9","align": "center"})

        #基本情報（データ部分）の書式
        info_data_format = workbook.add_format({"border": 1,"align": "center"})
        #入出庫履歴（ヘッダー部分）の書式
        header_format = workbook.add_format({
                "bold": True,
                "align": "center",
                "border": 1,
                "bg_color":"#D9D9D9"
                        })
                
        
        # 入出庫履歴（データ部分）の書式
        data_format = workbook.add_format({"border": 1,"align": "center"})
        
        #【幅などの設定】
        #列幅　worksheet.set_column("列範囲", 幅)
        worksheet.set_column("A:A", 19)
        worksheet.set_column("B:B", 10)
        worksheet.set_column("C:C", 10)
        worksheet.set_column("D:D", 16)
        worksheet.set_column("E:E", 12)
        worksheet.set_column("F:F", 12)

        #【実際の書き込み内容】
        # タイトル：A1～G1のセルを結合して書き込む
        worksheet.merge_range("A1:F1","在 庫 帳 簿",title_format)

        #備考
        worksheet.write("A7", "備考")

        #基本情報：worksheet.write(行, 列, 書き込む内容)セル名でもOK（ヘッダー・データ）
        worksheet.write("A3", "資材コード",info_header_format)#worksheet.write(行, 列, 書き込む内容,書式)セル名でもOK
        worksheet.write("B3", data.loc[item_condition,"資材コード"].iloc[0],info_data_format)
        worksheet.write("D3", "品名",info_header_format)
        worksheet.write("E3", data.loc[item_condition,"品名"].iloc[0],info_data_format)
        worksheet.write("A4", "型式・寸法",info_header_format)
        worksheet.write("B4", data.loc[item_condition,"型式・寸法"].iloc[0],info_data_format)
        worksheet.write("D4", "使用会社",info_header_format)
        worksheet.write("E4", data.loc[item_condition,"使用会社"].iloc[0],info_data_format)
        worksheet.write("A5", "形区分",info_header_format)
        worksheet.write("B5", data.loc[item_condition,"形区分"].iloc[0],info_data_format)

        #入出庫履歴（ヘッダー部分）：worksheet.write(行, 列, 内容, 書式) enumerate():番号と列名を同時に取れる
        for col_num, column_name in enumerate(ledger_data.columns):#columns:DataFrameの列名
            worksheet.write(7,col_num,column_name,header_format)

        # 入出庫履歴（データ部分）
        for row_num, (_, row) in enumerate(ledger_data.iterrows()):
        #row_num:連番 _:インデックス値を使わない
            # 1行の中から値を1個ずつ取り出す
            for col_num, value in enumerate(row):

                worksheet.write(row_num + 8,  # 9行目から順番に書き込む（スタート値）
                    col_num,value,data_format)

    # withを抜けるとExcelの書き込みが終了して完成

    # excel_dataの中から完成したExcelデータを取り出して返す
    return excel_data.getvalue()
#入出庫履歴検索用関数
def history_search(search_code_name):
    if search_code_name in st.session_state:
        condition=history_data["資材コード"]==st.session_state[search_code_name]
        display_count = st.selectbox("表示件数",[10, 20, 50])
        display_data = history_data.loc[condition].copy()
        display_data["日時"] = pd.to_datetime(display_data["日時"]).dt.date
        display_data = (display_data.sort_values("日時", ascending=False).head(display_count).sort_values("日時", ascending=True))
        item_name=history_data.loc[condition,"品名"].iloc[0]
        st.write(f"資材コード：{st.session_state[search_code_name]}")
        st.write(f"品名：{item_name}")
        st.dataframe(display_data.drop(columns=["資材コード", "品名"]), hide_index=True)
        #history_data.loc[condition] で対象の履歴だけ取り出す
        #→ copy() で表示用にコピー
        #→ コピー側の「日時」だけ日付に変更
        #→ 表示件数を決める
        #→ 新しい順に並べ替える
        #→ 表示件数分のデータが入る
        #→ 古い順に並べ替える
        #→ st.dataframe() で表示

        # 帳簿に使用する履歴を取得
        ledger_condition = history_data["資材コード"] == st.session_state["history_search_code"]
        ledger_data = history_data.loc[ledger_condition].copy()

        # 帳簿を作成
        excel_bytes = create_ledger(ledger_data,search_code_name)

        # 作成したExcelファイルをダウンロード
        st.download_button(
        "帳簿をダウンロード",    # ボタンに表示する名前
        data=excel_bytes,        # ダウンロードするデータ
        file_name=f"{item_name}_在庫帳簿.xlsx",  # 保存するときの名前
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                # xlsxファイルであることを指定
        )

#商品情報更新         
def stock_update(column_name,update_name):#商品情報更新用関数
    data.loc[data["資材コード"]== st.session_state["update_search_code"],column_name]=update_name

#検索（在庫検索・更新・削除・不足在庫・入出庫取消に使用）
def search_button_code(form_name,header_name,target_name,session_key):
    #検索用フォーム→チェック→コード維持保存用関数
    with st.form(form_name, clear_on_submit=True,enter_to_submit=False):
        st.header(header_name)
        st.write("資材コードを入力して検索ボタンを押してください")
        code=st.text_input("資材コード")
        submitted= st.form_submit_button("検索")
        
    if submitted:#更新用、削除用それぞれに判定される
        if not code.isdigit() or len(code)!= 8:
                st.error("資材コードは8桁の数字で入力してください") 
        elif  header_name=="入出庫履歴" or header_name=="入出庫取消":
            if not code in target_name["資材コード"].values:
                st.error("この資材コードの入出庫履歴はありません")
            else:
                st.session_state[session_key] = code
        else:
            if not code in target_name["資材コード"].values:
                st.error("この資材コードは登録されていません")
            else:
                st.session_state[session_key] = code

#条件別検索用関数
def search_by_pattern(form_name,sub_header_name,session_key):
    with st.form(form_name, clear_on_submit=True,enter_to_submit=False):
            st.subheader(sub_header_name)
            if sub_header_name=="使用会社":
                select_name=["A会社","B会社","その他"]
                select=st.selectbox("使用会社を選択してください",select_name)
            elif sub_header_name=="形区分":
                select_name=["A：製造","B：品管","C：事務所","D：物流"]
                select=st.selectbox("形区分を選択してください",select_name)
            submitted=st.form_submit_button("検索")#調べる項目を増やすときはここに追加
    if submitted:
        st.session_state[session_key]=select
        condition=data[sub_header_name]==st.session_state[session_key]
        if condition.any():
            st.subheader("商品情報")
            st.dataframe(data.loc[condition].drop(columns=["発注日","納入予定日"]),hide_index=True)
        else:
            st.error(f"{st.session_state[session_key]}の商品は登録されていません")

#発注書編集用関数
def order_sheet(order_condition, order_quantity):
    #【初期設定】
    code= data.loc[order_condition, "資材コード"].iloc[0]
    item= data.loc[order_condition, "品名"].iloc[0]
    model= data.loc[order_condition, "型式・寸法"].iloc[0]
    unit_price= data.loc[order_condition, "単価（税抜）"].iloc[0]
    price= unit_price*order_quantity
    order_date_sheet = pd.to_datetime(data.loc[order_condition, "発注日"].iloc[0]).strftime("%Y/%m/%d")
    #日付に変換してから表示形式を変える(発注日)　空白の場合は未定
    delivery_date_value = data.loc[order_condition, "納入予定日"].iloc[0]
    if pd.isna(delivery_date_value) or str(delivery_date_value).strip() == "":
        delivery_date_sheet = "未定"
    else:
        delivery_date_sheet = pd.to_datetime(delivery_date_value).strftime("%Y/%m/%d")
    #納入予定日
    order_source = data.loc[order_condition, "発注元"].iloc[0]
    source_condition = order_source_data["発注元"] == order_source
    postal_code = order_source_data.loc[source_condition, "郵便番号"].iloc[0]
    address = order_source_data.loc[source_condition, "住所"].iloc[0]
    tel = order_source_data.loc[source_condition, "電話番号"].iloc[0]
    fax = order_source_data.loc[source_condition, "FAX"].iloc[0]
    person = order_source_data.loc[source_condition, "担当者名"].iloc[0]
    # excel_data：完成したExcelデータを入れておく箱
    excel_data = BytesIO()
    # writer：Excelを作ってexcel_dataへ書き込むための窓口
    # with st.form()と同じように、with内がExcelを作成する範囲
    with pd.ExcelWriter(excel_data, engine="xlsxwriter") as writer:

         # workbook：writerが作成しているExcelブック全体
        workbook = writer.book

        # 「発注書」シートを新しく作る
        worksheet = workbook.add_worksheet("発注書")

        #【書式作成】
        ## タイトル
        title_format = workbook.add_format({
                    "bold": True,       # 太字
                    "font_size": 20,    # 文字サイズ
                    "align": "center",   # 中央揃え（横）
                    "valign": "vcenter"  #中央揃え（縦）
                })

        #基本情報・金額詳細（２項目）（ヘッダー部分）
        info_header_format = workbook.add_format({"border": 1,"bold": True,"bg_color":"#D9D9D9","align": "center"})

        #基本情報・発注元情報（データ部分）
        info_data_format = workbook.add_format({"border": 1,"align": "left","text_wrap": True})

        #発注元情報（ヘッダー部分）
        order_source_header_format = workbook.add_format({"border": 1,"bold": True,"bg_color":"#D9EAF7","align": "center"})

        # 発注明細（ヘッダー）
        order_header_format = workbook.add_format({
            "border": 1,
            "bold": True,
            "bg_color": "#D9EAF7",
            "align": "center",
            "valign": "vcenter",
            "font_name": "Yu Gothic",
            "font_size": 10
        })

        # 発注明細（データ）
        order_data_format = workbook.add_format({
            "border": 1,
            "align": "center",
            "valign": "vcenter",
            "font_name": "Yu Gothic",
            "font_size": 10
        })

        #金額部分
        price_format = workbook.add_format({
            "border": 1,
            "align": "center",
            "valign": "vcenter",
            "font_name": "Yu Gothic",
            "font_size": 10,
            "num_format": '#,##0"円"'
        })

        #税抜合計
        total_price_format= workbook.add_format({
            "border": 1,
            "bold": True,
            "align": "center",
            "valign": "vcenter",
            "font_name": "Yu Gothic",
            "font_size": 10,
            "num_format": '#,##0"円"'
        })

        #金額詳細（合計金額）
        total_price_header_format = workbook.add_format({"border": 1,"bold": True,"bg_color":"#D9EAF7","align": "center"})

        #【幅などの設定】
        #列幅　worksheet.set_column("列範囲", 幅)
        worksheet.set_column("A:A", 4)
        worksheet.set_column("B:B", 13)
        worksheet.set_column("C:C", 15)
        worksheet.set_column("D:D", 15)
        worksheet.set_column("E:E", 8)
        worksheet.set_column("F:F", 14)
        worksheet.set_column("G:G", 14)
        worksheet.set_column("H:H", 14)

        #【実際の書き込み内容】
        # タイトル：A1～G1のセルを結合して書き込む
        worksheet.merge_range("A1:H2","発注書",title_format)

        #基本情報：worksheet.write(行, 列, 書き込む内容)セル名でもOK（ヘッダー・データ）
        worksheet.merge_range("A4:B4", "発注先",info_header_format)#worksheet.write(行, 列, 書き込む内容,書式)セル名でもOK
        worksheet.merge_range("C4:D4",order_source,info_data_format)
        worksheet.merge_range("A5:B5", "発注日",info_header_format)
        worksheet.merge_range("C5:D5",order_date_sheet,info_data_format)
        worksheet.merge_range("A6:B6", "発注担当者",info_header_format)
        worksheet.merge_range("C6:D6",st.session_state["login_user"],info_data_format)
        worksheet.merge_range("A7:B7", "備考",info_header_format)
        worksheet.merge_range("C7:D7","下記の通り発注いたします",info_data_format)

        #発注元情報（ヘッダー・データ）
        worksheet.merge_range("F4:H4", "発注元情報",order_source_header_format)
        worksheet.merge_range("F5:H5", order_source, info_data_format)
        worksheet.merge_range("F6:H6", "〒" + postal_code, info_data_format)
        worksheet.merge_range("F7:H7", address, info_data_format)
        worksheet.merge_range("F8:H8", "TEL：" + tel + " FAX：" + fax, info_data_format)
        worksheet.merge_range("F9:H9", "担当者：" + person, info_data_format)

        #発注明細（ヘッダー）
        worksheet.write("A11", "No.", order_header_format)
        worksheet.write("B11", "資材コード", order_header_format)
        worksheet.write("C11", "品名", order_header_format)
        worksheet.write("D11", "型式・寸法", order_header_format)
        worksheet.write("E11", "発注数量", order_header_format)
        worksheet.write("F11", "単価（税抜）", order_header_format)
        worksheet.write("G11", "金額（税抜）", order_header_format)
        worksheet.write("H11", "納入予定日", order_header_format)

        #発注明細（データ）
        #表フォーマット
        # 12～21行目まで明細欄を作る　No.1→右空欄7つ→No.2→右空欄7つ
        # (外側のforが1周終わるには、中のforも全部終わる必要がある)
        for no in range(1, 11):#no.1～no10まで
            row_num = 10 + no

            # No.だけ最初から入力
            worksheet.write(row_num, 0, no, order_data_format)

            # その他は空欄（０列（NO.）から１つずつずらして空欄を作ってる）
            for col_num in range(1, 8):
                worksheet.write(row_num, col_num, "", order_data_format)
        #１行目の内容
        worksheet.write("B12", code, order_data_format)
        worksheet.write("C12", item, order_data_format)
        worksheet.write("D12", model, order_data_format)
        worksheet.write("E12", order_quantity, order_data_format)
        worksheet.write("F12", unit_price, price_format)
        worksheet.write("G12", price, price_format)
        worksheet.write("H12", delivery_date_sheet, order_data_format)

        #合計金額欄
        worksheet.merge_range("F23:G23", "税抜金額", info_header_format)
        worksheet.merge_range("F24:G24", "消費税（10％）", info_header_format)
        worksheet.merge_range("F25:G25", "税込合計", total_price_header_format)
        worksheet.write_formula("H23", "=SUM(G12:G21)", price_format)   
        worksheet.write_formula("H24", "=ROUND(H23*0.1,0)", price_format)  
        worksheet.write_formula("H25", "=H23+H24", total_price_format)  

    excel_data.seek(0)
    return excel_data

#発注内容変更関数
def order_change(cancel_change_condition, order_date, delivery_date,order_quantity):
    changed = False
    if order_date and delivery_date:#発注日・納入予定日があれば
        if order_date>delivery_date:
            st.error("発注日が納入予定日を過ぎています")
        elif order_quantity:#発注数量もあればすべて変更
            data.loc[cancel_change_condition, "発注日"] = str(order_date)
            data.loc[cancel_change_condition, "納入予定日"] = str(delivery_date)
            data.loc[cancel_change_condition, "発注数量"] = int(order_quantity)
            changed = True
            st.success("下記の通り、発注日・納入予定日・発注数量が変更されました")
        else:#発注日・納入予定日を変更
            data.loc[cancel_change_condition, "発注日"] = str(order_date)
            data.loc[cancel_change_condition, "納入予定日"] = str(delivery_date)
            changed = True
            st.success("下記の通り、発注日・納入予定日が変更されました")
    elif order_date:#発注日があれば
        code_delivery_date = data.loc[cancel_change_condition, "納入予定日"].iloc[0]
        if pd.notna(code_delivery_date):#code_delivery_dateにデータがあるなら
            code_delivery_date = pd.to_datetime(code_delivery_date).date()#比較のためdate型にそろえる
            if order_date>code_delivery_date:
                st.error("発注日が納入予定日を過ぎています")
            elif order_quantity:#発注数量もあれば発注日・発注数量変更
                data.loc[cancel_change_condition, "発注日"] = str(order_date)
                data.loc[cancel_change_condition, "発注数量"] = int(order_quantity)
                changed = True
                st.success("下記の通り、発注日・発注数量が変更されました")
            else:#発注日のみ
                data.loc[cancel_change_condition, "発注日"] = str(order_date)
                changed = True
                st.success("下記の通り、発注日が変更されました")
        else:#納入予定日が事前に入ってないなら
            if order_quantity:#発注数量もあれば発注日・発注数量変更
                data.loc[cancel_change_condition, "発注日"] = str(order_date)
                data.loc[cancel_change_condition, "発注数量"] = int(order_quantity)
                changed = True
                st.success("下記の通り、発注日・発注数量が変更されました")
            else:
                data.loc[cancel_change_condition, "発注日"] = str(order_date)
                changed = True
                st.success("下記の通り、発注日が変更されました")
    elif delivery_date:#納入予定日があれば
        code_order_date = data.loc[cancel_change_condition, "発注日"].iloc[0]
        if pd.notna(code_order_date):
            code_order_date = pd.to_datetime(code_order_date).date()
            if delivery_date<code_order_date:
                st.error("納入予定日は発注日より後日にしてください")
            elif order_quantity:#発注数量もあれば納入予定日・発注数量変更
                data.loc[cancel_change_condition, "納入予定日"] = str(delivery_date)
                data.loc[cancel_change_condition, "発注数量"] = int(order_quantity)
                changed = True
                st.success("下記の通り、納入予定日・発注数量が変更されました")
            else:#納入予定日を変更
                data.loc[cancel_change_condition, "納入予定日"] = str(delivery_date)
                changed = True
                st.success("下記の通り、納入予定日が変更されました")
        else:#基本的は発注日はあるはずだがファイルが壊れた時などの保険
            st.error("発注日が登録されていません")
    elif order_quantity:#発注数量だけ変更
        data.loc[cancel_change_condition, "発注数量"] = int(order_quantity)
        changed = True
        st.success("下記の通り、発注数量が変更されました")
    else:
        st.error("いずれかを入力してください")
    return changed

#入出庫取消用関数
def cancel_type_check(cancel_type):
    with st.form("stock_cancel", clear_on_submit=True,enter_to_submit=False):
        st.markdown(f"<span style='color:red;'>上記の情報を取り消します!<br>ご確認の上、取消ボタンを押してください</span>",
                    unsafe_allow_html=True)
        submitted_cancel = st.form_submit_button("取消")
    if submitted_cancel:
        canceled = False
        if cancel_type=="入庫":
            if data.loc[cancel_condition, "在庫数"].iloc[0]<cancel_amount:
                st.error("在庫数が不足のため取消できません")
            else:
                data.loc[cancel_condition, "在庫数"] -= cancel_amount
                canceled = True
        elif cancel_type == "出庫":
            data.loc[cancel_condition, "在庫数"] += cancel_amount
            canceled = True
        if canceled:
            cancel_item=data.loc[cancel_condition, "品名"].iloc[0]
            cancel_current_stock=data.loc[cancel_condition, "在庫数"].iloc[0]
            history_data.loc[selected_index, "取消状況"] = "有"
            save()
            history_save(cancel_condition, cancel_amount, cancel_item , cancel_type+"取消", cancel_current_stock ,"━")
            st.success("取消が実行されました")
#ここから実行コード

#ログイン画面
if "login_user" not in st.session_state:

    with st.form("login_form"):

        user_list = list(st.secrets["users"].keys())
        #key()でst.secrets["users"]の左側、辞書で言うkeyを取っている
        user_id = st.selectbox("ID", user_list)
        password = st.text_input("パスワード", type="password")
        #type="password" ••••••••隠れる
        submitted = st.form_submit_button("ログイン")

    if submitted:
        if user_id in st.secrets["users"]:
            #入力したIDが登録されているか(secrets["users"]に入っていない)
            if bcrypt.checkpw(
                        password.encode("utf-8"),
                        st.secrets["users"][user_id].encode("utf-8")
                    ):
                #secrets.tomlのusersのuser_idと一致したものを取り出す
                #＝secrets.tomlでパスワードを代入しているのでそのパスワードが入る
                #そのパスワードと入力したパスワードが一致すれば
                st.session_state["login_user"] = user_id
                #ログイン中のユーザーIDが入る
                st.session_state["login_role"] = st.secrets["roles"][user_id]
                #ログイン中のユーザーIDに対応する権限をlogin_roleに保存
                st.rerun()
                #画面の最初に戻るがif "login_user" not in st.session_state:
                #に流れないためアプリに入る
            else:#一致してないため
                st.error("パスワードが違います")
        else:#登録されていないため
            st.error("IDが登録されていません")
else:   
    #保存関係
    conn=st.connection("gsheets", type=GSheetsConnection)
    #「gsheetsという設定を使って、Googleスプレッドシートとの接続を作ってね」

    #在庫一覧データ
    data=conn.read(spreadsheet=SHEET_URL,ttl=0)
    #data:スプレッドシートから読み込んだデータを入れておく変数,conn.read():スプレッドシートを読み込む
    #ttl=0は、ざっくり言えば読み込み結果を長くキャッシュせず、最新のシートを読み直すための設定
    data = data.dropna(subset=["資材コード"])
    # 資材コードが空欄の行を除外
    data["資材コード"] = (data["資材コード"].astype(int).astype(str).str.zfill(8))
        #入力値のcode等は文字列だがスプレットシートに入ってるのは数字のため、整数化→文字列
        #→この列の各文字列に対して文字列処理をする(str)→プログラム上で使える8桁にするを行い、比較等可能にする
    data["型式・寸法"] = data["型式・寸法"].astype("object")#文字列など色々な値を入れられる型
    data["発注日"] = data["発注日"].astype("object")#空欄が多いとfloat64になることがあるため変換
    data["納入予定日"] = data["納入予定日"].astype("object")
    data["発注元"] = data["発注元"].astype("object")

    #入出庫履歴データ
    history_data = conn.read(spreadsheet=SHEET_URL, worksheet="入出庫履歴",ttl=0)
    history_data = history_data.dropna(subset=["資材コード"])
    history_data["資材コード"] = (history_data["資材コード"].astype(int).astype(str).str.zfill(8))

    #発注履歴データ
    order_data = conn.read(spreadsheet=SHEET_URL, worksheet="発注履歴",ttl=0)
    order_data = order_data.dropna(subset=["資材コード"])
    order_data["資材コード"] = (order_data["資材コード"].astype(int).astype(str).str.zfill(8))
    order_data["発注日"] = order_data["発注日"].astype("object")
    order_data["納入予定日"] = order_data["納入予定日"].astype("object")

    #発注元マスタデータ
    order_source_data = conn.read(spreadsheet=SHEET_URL,worksheet="発注元マスタ",ttl=0)

    inventory_data = conn.read(spreadsheet=SHEET_URL,worksheet="棚卸モード切替用（触らない）",ttl=0)
    #初期値OFF
  

    col1,col2=st.columns([3,1])
    #メインタイトル
    with col1:
        st.title("資材管理システム")

    #ログアウト
    with col2:
        st.write(f"ログイン中：{st.session_state['login_user']}")
        if st.button("ログアウト"):
            del st.session_state["login_user"]
            del st.session_state["login_role"]
            st.rerun()

    #棚卸モード
    if st.session_state["login_role"] == "管理者":
        inventory_btton= st.button("棚卸モード")
        if inventory_btton:
            if  inventory_data["棚卸モード"].iloc[0]=="OFF":
                inventory_data.loc[inventory_data["棚卸モード"]=="OFF","棚卸モード"]="ON"
                st.success("棚卸モードをONにしました")
            else:
                inventory_data.loc[inventory_data["棚卸モード"]=="ON","棚卸モード"]="OFF"
                st.success("棚卸モードをOFFにしました")
            conn.update(
            spreadsheet=SHEET_URL,
            worksheet="棚卸モード切替用（触らない）",
            data=inventory_data)

        st.write(f"現在の状態：{inventory_data["棚卸モード"].iloc[0]}")
    #タブ全体管理
    #発注状況表示（tab5）
    order_required = ((data["在庫数"] < data["最低在庫数"]) &(data["発注日"].isna()))
    if order_required.any():
        order_tab_name = "⚠️ 発注状況"
    else:
        order_tab_name = "発注状況"

    tab1,tab2,tab3,tab4,tab5,tab6= st.tabs(
        ["入庫", "出庫", "在庫確認","商品管理",order_tab_name,"入出庫取消"])

    #在庫確認タブ
    with tab3:
        history_tub,search_tub,show_tub=st.tabs(["入出庫履歴（倉出管理表）","在庫検索","在庫一覧"])

    #在庫検索タブ(3段目)
    with search_tub:
        code_search_tub,pattern_search_tub=st.tabs(["資材コード検索","条件別検索"])

    #登録管理タブ
    with tab4:
        register_tab,update_tab, delete_tab = st.tabs(
            ["商品登録","商品情報更新", "商品削除"])

    #発注状況タブ
    with tab5:
        order_tub , already_ordered_tub= st.tabs(
                ["発注","発注情報変更（取消）"])
    
    #入庫用フォーム（タブ）
    with tab1:
        if (inventory_data["棚卸モード"].iloc[0] 
                        == "ON" and st.session_state["login_role"] != "管理者"):
            st.warning("現在棚卸中のため、入出庫できません")
        else:
            code,item,amount,submitted_stock=stock_in_out_form("stock_in_form","入庫","入庫数")

            #入庫用チェック機能    
            if submitted_stock:
                stock_in_out_check("入庫")

    #出庫用フォーム（タブ）
    with tab2:
        if (inventory_data["棚卸モード"].iloc[0] 
            == "ON" and st.session_state["login_role"] != "管理者"):
            st.warning("現在棚卸中のため、入出庫できません")
        else:
            code,item,amount,submitted_stock=stock_in_out_form("stock_out_form","出庫","出庫数") 

            #出庫用チェック機能
            if submitted_stock:
                stock_in_out_check("出庫")
            
    #入出庫履歴
    with history_tub:
        search_button_code("stock_history_search","入出庫履歴（倉出管理表）",history_data,"history_search_code")
        history_search("history_search_code")
        
    #在庫検索
    #資材コード検索
    with code_search_tub:
        search_button_code("stock_search","在庫検索",data,"search_code")
        if "search_code" in st.session_state:
            st.subheader("商品情報")
            condition=data["資材コード"]==st.session_state["search_code"]
            st.dataframe(data.loc[condition].drop(columns=["発注日","納入予定日"]),hide_index=True)

    #条件別検索
    with pattern_search_tub:
        #使用会社
        search_by_pattern("stock_company_search_form","使用会社","company_search_select")
        #形区分
        search_by_pattern("stock_section_search_form","形区分","section_search_select")
                
    #在庫一覧
    with show_tub:
        with st.container(border=True):#下部をひとつにまとめる、border=True（枠を作る）
            #閲覧者を増やす場合は共有に追加
            st.header("在庫一覧")
            st.write("在庫を確認できます")
            col1,col2,col3=st.columns([1,1,1])
            with col1:
                all_button=st.button("全品目", use_container_width=True)
            show_stock (all_button)
                
            with col2:
                company_button=st.button("使用会社別", use_container_width=True)
            show_stock (company_button,"使用会社","A会社")
            show_stock (company_button,"使用会社","B会社")
            show_stock (company_button,"使用会社","その他")

            with col3:
                section_button=st.button("形区分別", use_container_width=True)
            show_stock (section_button,"形区分","A：製造")
            show_stock (section_button,"形区分","B：品管")
            show_stock (section_button,"形区分","C：事務所")
            show_stock (section_button,"形区分","D：物流")
            

    #登録用フォーム
    with register_tab:
        if st.session_state["login_role"] == "管理者":
            with st.form("register_form", clear_on_submit=True,enter_to_submit=False):
                st.header("商品登録")#サブタイトル
                left,right=st.columns(2)
                with left:
                    code=st.text_input("資材コードを入力してください")
                    item=st.text_input("品名を入力してください")
                    model=st.text_input("型式・寸法を入力してください")
                    stock=st.number_input("在庫数",min_value=0)
                    min_stock=st.number_input("最低在庫数",min_value=1)
                    confirm_min_stock = st.checkbox("最低在庫数を１個で登録する場合はこちらにチェック")
                with right:
                    company_name=["A会社","B会社","その他"]
                    company=st.selectbox("使用会社を選択してください",company_name)
                    section_name=["A：製造","B：品管","C：事務所","D：物流"]
                    section=st.selectbox("形区分を選択してください",section_name)
                    unit_price = st.number_input("単価（税抜）※不明の場合は0のまま", min_value=0)
                    order_source_name=data["発注元"].dropna().unique().tolist()#列から重複無し・None 無しでリスト化
                    order_source_name.insert(0,"")#リストの頭に空白を追加
                    select_order_source = st.selectbox("発注元を履歴から選択する場合はこちらから",order_source_name)
                    order_source = st.text_input("発注元を新規に入力する場合はこちらから")
                submitted=st.form_submit_button("登録")
            # form：複数の入力項目と送信ボタンを1セットにする,登録用紙全体
            # submitted：登録ボタンが押されたかを受け取る,その用紙の「登録する」ボタン

            #登録用チェック機能
            if submitted:
                if not code.isdigit() or len(code)!= 8:
                        st.error("資材コードは8桁の数字で入力してください") 
                elif code in data["資材コード"].values:
                    st.error("この資材コードは既に登録されています") 
                elif not item.strip():
                    st.error("品名を入力してください")
                elif min_stock==1 and not confirm_min_stock:#最低在庫数が1でチェックが入って無ければ
                    st.error("最低在庫数：チェックを入れるか数量を変更してください")
                elif select_order_source and order_source:
                    st.error("発注元はどちらかひとつに入力してください")
                elif not select_order_source and not order_source.strip():
                    st.error("発注元をいずれかに入力してください")
                else:
                    if select_order_source:
                        order_source = select_order_source
                    new_data = pd.DataFrame([{
                "資材コード": code,
                "品名": item,
                "型式・寸法": model,
                "在庫数": stock,
                "最低在庫数": min_stock,
                "使用会社": company,
                "形区分": section,
                "発注日": None,
                "発注数量":None,
                "単価（税抜）":unit_price,
                "発注元":order_source
            }])#入力した8項目を、スプレッドシートの1行分の表にする
                # 発注済みはGoogleスプレッドシートへの書き戻し時に
                # チェックボックスではなくTRUE/FALSE表示になるため現状維持

                    data = pd.concat([data, new_data], ignore_index=True) 
                    #concatは「つなげる」というイメージでOK。
                    data = data.sort_values("資材コード").reset_index(drop=True)
                    #資材コード順に並べる
                    save()
                    condition=data["資材コード"]==code
                    st.write("以下のデータを登録しました")
                    st.dataframe(data.loc[condition].drop(columns=["発注日","納入予定日"]),hide_index=True)
        else:
            st.warning("商品情報を変更する権限がありません")        

    #商品情報更新（検索機能・更新フォーム・更新チェックあり）
    with update_tab:
        if st.session_state["login_role"] == "管理者":
            search_button_code("stock_update_search","商品情報更新",data,"update_search_code")
            if "update_search_code" in st.session_state:
                with st.form("stock_update", clear_on_submit=True,enter_to_submit=False):#更新用フォーム
                    st.subheader("現在の情報")
                    condition=data["資材コード"]==st.session_state["update_search_code"]
                    st.dataframe(data.loc[condition,["資材コード", "品名", "型式・寸法", "最低在庫数","使用会社","単価（税抜）","発注元"]],hide_index=True)
                    st.subheader("更新情報の入力")
                    st.write("※変更しない項目は空欄（最低在庫数・単価（税抜）は0）のままにしてください")
                    up_item=st.text_input("品名")
                    up_model=st.text_input("型式・寸法")
                    up_min_stock=int(st.number_input("最低在庫数",min_value=0))
                    up_company_name=["","A会社","B会社","その他"]
                    up_company=st.selectbox("使用会社",up_company_name)
                    up_unit_price = st.number_input("単価（税抜)", min_value=0)
                    up_order_source = st.text_input("発注元")
                    submitted_stock_update = st.form_submit_button("更新")

                if submitted_stock_update:#更新チェック
                    update_notes=[]#更新内容表示用
                    if up_item:
                        stock_update("品名",up_item)
                        update_notes.append("品名")
                    if up_model:
                        stock_update("型式・寸法",up_model)
                        update_notes.append("型式・寸法")
                    if up_min_stock:
                        stock_update("最低在庫数",up_min_stock)
                        update_notes.append("最低在庫数")
                    if up_company:
                        stock_update("使用会社",up_company)
                        update_notes.append("使用会社")
                    if up_unit_price:
                        stock_update("単価（税抜）",up_unit_price)
                        update_notes.append("単価（税抜）")
                    if up_order_source:
                        stock_update("発注元",up_order_source)
                        update_notes.append("発注元")
                    if not up_item and not up_model and not up_min_stock and not up_company and not up_order_source and not up_unit_price: 
                        st.error("いずれかを入力してください")
                    if  update_notes:
                        save()
                        st.subheader("今回の更新情報")
                        for update_note in update_notes:#
                            st.write(f"◆{update_note}")
                        st.dataframe(data.loc[condition,[ "資材コード","品名", "型式・寸法", "最低在庫数","使用会社","単価（税抜）","発注元"]],hide_index=True)
        else:
            st.warning("商品情報を変更する権限がありません")

    #商品削除（検索機能・削除フォーム・削除チェックあり）
    with delete_tab:
        if st.session_state["login_role"] == "管理者":
            search_button_code("stock_delete_search","商品削除",data,"delete_search_code")
            if "delete_search_code" in st.session_state:
                with st.form("stock_delete", clear_on_submit=True,enter_to_submit=False):#削除用フォーム
                    st.subheader("削除する情報")
                    condition=data["資材コード"]==st.session_state["delete_search_code"]
                    st.dataframe(data.loc[condition],hide_index=True)
                    confirm = st.checkbox("この商品を削除することを確認しました")#チェックボックス
                    submitted_delete = st.form_submit_button("削除")
                if submitted_delete:
                    if confirm:#チェックが入っていれば
                        data = data.drop(data.loc[condition].index)#data内のdrop指定されたindexの行を削除
                        save()
                        st.success("上記の情報は削除されました")
                    else:
                        st.warning("確認欄にチェックを入れてください")
        else:
            st.warning("商品情報を変更する権限がありません")

    #発注
    with order_tub:
        condition =((data["在庫数"] < data["最低在庫数"]) &
        (data["発注日"].isna()))#isna() は、その値が NaN（欠損値・空欄）かどうかを見る
        if condition.any():#condition(最低在庫数以下の在庫数)の中にTrueが1つでもあるなら
            if st.session_state["login_role"] in ["発注担当", "管理者"]:
                search_button_code("order_search","発注",data,"order_search_code")
                if "order_search_code" in st.session_state:
                    order_condition = (
                    (data["資材コード"] == st.session_state["order_search_code"]) &
                    (data["在庫数"] < data["最低在庫数"]) &
                    (data["発注日"].isna())
                    )
                    if order_condition.any():
                        with st.form("order_form",clear_on_submit=True,enter_to_submit=False):
                            st.subheader("現在の情報")
                            st.dataframe(data.loc[order_condition,["資材コード", "品名", "型式・寸法","在庫数","最低在庫数"]],hide_index=True)
                            order_date = st.date_input("発注日", value=date.today())
                            delivery_date = st.date_input("納入予定日 ※未定の場合は空欄のままにしてください", value=None)
                            order_quantity = st.number_input("発注数量",value=1,min_value=1)
                            confirm_order_quantity = st.checkbox("発注数量を１個で発注する場合はこちらにチェック")
                            submitted_order = st.form_submit_button("発注")
                        if submitted_order:
                            order_source = data.loc[order_condition, "発注元"].iloc[0]
                            unit_price = int(data.loc[order_condition, "単価（税抜）"].iloc[0])
                            if not order_source:
                                st.error("発注元が登録されていません。商品情報更新から発注元を登録してください")  
                            elif not order_source in order_source_data["発注元"].values:
                                st.error("発注元がマスタデータに登録されていません。PCから登録してください")  
                            elif unit_price == 0:
                                st.error("単価が登録されていません。商品情報更新から単価を登録してください")
                            elif not order_date:
                                st.error("発注日を入力してください")
                            elif delivery_date and order_date>delivery_date:
                                st.error("発注日が納入予定日を過ぎています")
                            elif order_quantity==1 and not confirm_order_quantity:
                                st.error("発注数：チェックを入れるか数量を変更してください")     
                            else:
                                current_stock = data.loc[order_condition, "在庫数"].iloc[0]
                                min_stock = data.loc[order_condition, "最低在庫数"].iloc[0]
                                if current_stock + order_quantity < min_stock:
                                    st.warning("※納入後も最低在庫数を下回ります。発注数量を確認してください")
                                data.loc[order_condition, "発注日"] = str(order_date) #左のままだと文字列ではなくdate 型。
                                data.loc[order_condition, "発注数量"] = int(order_quantity)
                                if delivery_date:
                                    data.loc[order_condition, "納入予定日"] = delivery_date
                                save()
                                if delivery_date:
                                    save_delivery_date = delivery_date
                                else:
                                    save_delivery_date = "━"
                                order_save(order_condition,"発注",order_date,save_delivery_date, order_quantity)
                                st.success("下記の通り、発注されました、発注書をダウンロードしてください")
                                st.dataframe(data.loc[order_condition,
                                                        ["資材コード","品名","型式・寸法","発注日","納入予定日","発注数量","単価（税抜）","発注元"]]
                                                        ,hide_index=True)
                                st.warning("※発注書を保存するまで、この画面を閉じないでください")
                                order_excel = order_sheet(order_condition, order_quantity)
                                st.download_button(
                                    label="発注書をダウンロード",
                                    data=order_excel,
                                    file_name="発注書.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                               )
                    else:
                        st.error("この商品は現在、発注対象ではありません") 

            else:
                st.warning("発注権限がありません")
            st.subheader("⚠️ 発注確認")
            st.markdown(f"<span style='color:red;'>不足している部品が{condition.sum()}個あります、発注してください！</span>",
                unsafe_allow_html=True
            )#unsafe_allow_html=True → HTMLによる色・サイズなどの装飾を許可
            #conditionの中にTrueがいくつあるか（Trueは1　Falseは0　1の合計）
            #lenはTrueとFalseどっちの数も拾うためpandas（表）には使えない
            st.dataframe(data.loc[condition,["資材コード", "品名", "型式・寸法", "在庫数", "最低在庫数","発注元"]],hide_index=True)

        else:
            st.caption("✓ 不足している部品（未発注）はありません")

    #発注情報更新（検索機能・変更/検索フォーム・更新チェック（関数）あり）
    with already_ordered_tub: 
        already_ordered=data["発注日"].notna()#notna() は、その値が 入ってるかどうかを見る   
        if already_ordered.any():#発注済みにTrueな物が一つでもあれば
            if st.session_state["login_role"] in ["発注担当", "管理者"]:
                #発注情報更新フォーム(検索あり)
                search_button_code("order_cancel_change_search","発注情報変更（取消）",data,"cancel_change_search_code")
                if "cancel_change_search_code" in st.session_state:
                    cancel_change_condition = ((data["資材コード"] == st.session_state["cancel_change_search_code"]) &
                    (data["発注日"].notna()))#資材コードと一致かつ発注日があるもの
                    if cancel_change_condition.any():
                        with st.form("order_cancel_change_form",clear_on_submit=True,enter_to_submit=False):
                            st.subheader("現在の情報")
                            st.dataframe(data.loc[cancel_change_condition].drop(columns=["使用会社","形区分","発注元"]),hide_index=True)
                            st.subheader("更新情報の入力")
                            st.write("※更新しない項目は空欄（発注数量は0）のままにしてください")
                            st.write("※発注取消の場合はすべて空欄のまま【発注取消ボタン】を押してください")
                            order_date = st.date_input("発注日", value=None)
                            delivery_date = st.date_input("納入予定日" ,value=None)
                            order_quantity = st.number_input("発注数量",value=0,min_value=0)

                            submitted_order_cancel = st.form_submit_button("発注取消")
                            submitted_order_change = st.form_submit_button("発注内容変更")
                            if submitted_order_cancel or submitted_order_change:
                                changed = False
                                if submitted_order_cancel:
                                    data.loc[cancel_change_condition, "発注日"] = None
                                    data.loc[cancel_change_condition, "納入予定日"] = None
                                    data.loc[cancel_change_condition, "発注数量"] = None
                                    changed = True
                                    order_save(cancel_change_condition,"発注取消","取消","取消","取消")
                                    st.success("発注を取り消しました")
                                    st.warning("※保存済みの発注書がある場合は、使用しないように発注書を削除してください")
                                    
                                elif submitted_order_change:
                                    changed=order_change(cancel_change_condition, order_date, delivery_date,order_quantity)
                                    if changed:
                                        if order_date==None:
                                            save_order_date="━"
                                        else:
                                            save_order_date=order_date
                                        if delivery_date==None:
                                            save_delivery_date="━"
                                        else:
                                            save_delivery_date=delivery_date
                                        if order_quantity==0:
                                            save_order_quantity="━"
                                        else:
                                            save_order_quantity=order_quantity
                                        order_save(cancel_change_condition, "発注内容変更",save_order_date,save_delivery_date,save_order_quantity)
                                        st.warning("※保存済みの発注書がある場合は、発注書の内容も更新してください")
                                if changed:
                                    save()
                                    st.dataframe(data.loc[cancel_change_condition].drop(columns=["使用会社","形区分","発注元"]),hide_index=True)
                    else:
                        st.error("この商品は発注されていません")
            else:
                st.warning("発注権限がありません")
            st.markdown(
            "<h3><span style='color:green;'>★</span>&nbsp;&nbsp;発注済み商品</h3>",
            unsafe_allow_html=True)
            #span は、文章の一部分だけ色や太さなどを変えたいときに、その範囲を囲むもの
            #<span> ～ </span> <h3> ～ </h3>
            #<h3> ～ </h3> → 全体の文字サイズ
            #<span>★</span> → ★だけ追加で色を変更
            #&nbsp;は空白１個
            st.dataframe(data.loc[already_ordered,["資材コード", "品名", "在庫数","発注日","納入予定日","発注数量"]],hide_index=True)
            
        else:
            st.caption("✓ 発注している部品はありません")

    #入出庫取消
    with tab6:
        search_button_code("stock_cancel_search","入出庫取消",history_data,"cancel_search_code")
        # ① 資材コードで履歴を絞る
        if "cancel_search_code" in st.session_state:#履歴から選ぶ
            condition = (
        (history_data["資材コード"] == st.session_state["cancel_search_code"]) &
        (history_data["区分"].isin(["入庫", "出庫"])) &#ここ今は不要、今後「取消状況」の状態次第で使えるかも
        (history_data["取消状況"]=="無"))#history_data["区分"]の中に"入庫", "出庫"が入ってるか
            cancel_history = history_data.loc[condition]
            # ② indexを選択肢にする
            if cancel_history.empty:#.empty = 「この表、空？」
                st.error("取消可能な入出庫履歴はありません")
            else:
                selected_index = st.selectbox(
                    "取り消す履歴を選択してください",
                    cancel_history.index,
                    # ③ ただし画面にはindexからの履歴内容を表示
                    format_func=lambda i: (
                        f'{cancel_history.loc[i, "日時"]} '
                        f'{cancel_history.loc[i, "区分"]} '
                        f'{int(cancel_history.loc[i, "数量"])}個'
                        f'{cancel_history.loc[i, "作業者"]}'
                    )
                )
                # ④ 選んだindexから元の履歴を取得
                cancel_data = history_data.loc[selected_index]
                #history_dataの中の選んだインデックス値に対応する行を代入
                cancel_code = cancel_data["資材コード"]
                cancel_type = cancel_data["区分"]
                cancel_amount = int(cancel_data["数量"])
                #それぞれ、cancel_dataの中から各ヘッダーの値を代入
                cancel_condition = data["資材コード"] == cancel_code
                #dataの資材コードとhistory_dataの資材コード（cancel_code）一致した行
                cancel_type_check(cancel_type)
                
                                            

                    

