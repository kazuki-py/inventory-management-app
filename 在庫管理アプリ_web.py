#ここから初期設定
import streamlit as st
#Streamlit本体。入力欄やボタン、画面表示などを作るために使う
import pandas as pd
#スプレッドシートから読み込んだ表データをPythonで扱いやすくする
from streamlit_gsheets import GSheetsConnection
#StreamlitとGoogleスプレッドシートを接続するための機能
from datetime import datetime,date
#入出庫した瞬間の日時を取得
SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]#URLを隠す[]の所から持ってくる
#ここから関数

    
#データ保存
def save():#更新後のdataをスプレッドシートへ書き戻す
           # data=data：変更後のdata（表）をスプレッドシートに渡して更新
    conn.update(
        spreadsheet=SHEET_URL,
        data=data)
    
#履歴保存
def history_save(condition, amount, item_name, stock_typ, current_stock,cancel_situation):
    global history_data
    code_number = data.loc[condition, "資材コード"].iloc[0]
    now = datetime.now().strftime("%Y/%m/%d %H:%M:%S")#その瞬間の日時がnowに入る　表示方法2026/08/16 16:52:31
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
    st.success(f"{item_name}を{amount}個{stock_typ}しました")
    st.write(f"現在の在庫数：{current_stock}個")

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

#入出庫履歴用関数
def history_search(search_code_name):
    if search_code_name in st.session_state:
        st.subheader("入出庫履歴")
        condition=history_data["資材コード"]==st.session_state[search_code_name]
        display_count = st.selectbox("表示件数",[10, 20, 50])
        display_data = history_data.loc[condition].copy()
        display_data["日時"] = pd.to_datetime(display_data["日時"]).dt.date
        display_data = (display_data.sort_values("日時", ascending=False).head(display_count))
        item_name=history_data.loc[condition,"品名"].iloc[0]
        st.write(f"資材コード：{st.session_state[search_code_name]}")
        st.write(f"品名：{item_name}")
        st.dataframe(display_data.drop(columns=["資材コード", "品名"]), hide_index=True)
        #history_data.loc[condition] で対象の履歴だけ取り出す
        #→ copy() で表示用にコピー
        #→ コピー側の「日時」だけ日付に変更
        #→ 表示件数を決める
        #→ 表示件数分のデータが入る
        #→ st.dataframe() で表示

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

#発注内容変更関数
def order_change(cancel_change_condition, order_date, delivery_date):
    changed = False
    if order_date and delivery_date:#発注日・納入予定日どちらも変更
        if order_date>delivery_date:
            st.error("発注日が納入予定日を過ぎています")
        else:
            data.loc[cancel_change_condition, "発注日"] = str(order_date)
            data.loc[cancel_change_condition, "納入予定日"] = str(delivery_date)
            changed = True
            st.success("下記の通り、発注日・納入予定日が変更されました")
    elif order_date:#発注日だけ変更
        code_delivery_date = data.loc[cancel_change_condition, "納入予定日"].iloc[0]
        if pd.notna(code_delivery_date):#code_delivery_dateにデータがあるなら
            code_delivery_date = pd.to_datetime(code_delivery_date).date()#比較のためdate型にそろえる
            if order_date>code_delivery_date:
                st.error("発注日が納入予定日を過ぎています")
            else:
                data.loc[cancel_change_condition, "発注日"] = str(order_date)
                changed = True
                st.success("下記の通り、発注日が変更されました")
        else:
            data.loc[cancel_change_condition, "発注日"] = str(order_date)
            changed = True
            st.success("下記の通り、発注日が変更されました")
    elif delivery_date:#納入予定日だけ変更
        code_order_date = data.loc[cancel_change_condition, "発注日"].iloc[0]
        if pd.notna(code_order_date):
            code_order_date = pd.to_datetime(code_order_date).date()
            if delivery_date<code_order_date:
                st.error("納入予定日は発注日より後日にしてください")
            else:
                data.loc[cancel_change_condition, "納入予定日"] = str(delivery_date)
                changed = True
                st.success("下記の通り、納入予定日が変更されました")
        else:#基本的は発注日はあるはずだがファイルが壊れた時などの保険
            st.error("発注日が登録されていません")    
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
            if st.secrets["users"][user_id] == password:
                #secrets.tomlのusersのuser_idと一致したものを取り出す
                #＝secrets.tomlでパスワードを代入しているのでそのパスワードが入る
                #そのパスワードと入力したパスワードが一致すれば
                st.session_state["login_user"] = user_id
                #ログイン中のユーザーIDが入る
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

    data=conn.read(spreadsheet=SHEET_URL,ttl=0)#在庫データ
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

    #履歴データ
    history_data = conn.read(spreadsheet=SHEET_URL, worksheet="入出庫履歴",ttl=0)
    history_data = history_data.dropna(subset=["資材コード"])
    history_data["資材コード"] = (history_data["資材コード"].astype(int).astype(str).str.zfill(8))

    col1,col2=st.columns([3,1])
    #メインタイトル
    with col1:
        st.title("在庫管理アプリ")
    with col2:
        st.write(f"ログイン中：{st.session_state['login_user']}")
        if st.button("ログアウト"):
            del st.session_state["login_user"]
            st.rerun()

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
        search_tub,history_tub,show_tub=st.tabs(["在庫検索","入出庫履歴","在庫一覧"])

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
                ["発注","発注情報更新"])
    
    #入庫用フォーム（タブ）
    with tab1:
        code,item,amount,submitted_stock=stock_in_out_form("stock_in_form","入庫","入庫数")

    #入庫用チェック機能    
    if submitted_stock:
        stock_in_out_check("入庫")

    #出庫用フォーム（タブ）
    with tab2:
        code,item,amount,submitted_stock=stock_in_out_form("stock_out_form","出庫","出庫数") 

    #出庫用チェック機能
    if submitted_stock:
        stock_in_out_check("出庫")

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

    #入出庫履歴
    with history_tub:
        search_button_code("stock_history_search","入出庫履歴",history_data,"history_search_code")
        history_search("history_search_code")
        
    #在庫一覧
    with show_tub:
        with st.container(border=True):#下部をひとつにまとめる、border=True（枠を作る）
            #閲覧者を増やす場合は共有に追加
            st.header("在庫一覧")
            st.write("在庫を確認できます")
            st.link_button("在庫一覧を開く",SHEET_URL)
    
    #登録用フォーム
    with register_tab:
        with st.form("register_form", clear_on_submit=True,enter_to_submit=False):
            st.header("商品登録")#サブタイトル
            left,right=st.columns(2)
            with left:
                code=st.text_input("資材コードを入力してください")
                item=st.text_input("品名を入力してください")
                model=st.text_input("型式・寸法を入力してください")
                stock=st.number_input("在庫数",min_value=0)
            with right:
                company_name=["A会社","B会社","その他"]
                company=st.selectbox("使用会社を選択してください",company_name)
                section_name=["A：製造","B：品管","C：事務所","D：物流"]
                section=st.selectbox("形区分を選択してください",section_name)
                min_stock=st.number_input("最低在庫数",min_value=1)
                confirm_min_stock = st.checkbox("最低在庫数を１個で登録する場合はこちらにチェック")
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
        else:
            new_data = pd.DataFrame([{
        "資材コード": code,
        "品名": item,
        "型式・寸法": model,
        "在庫数": stock,
        "最低在庫数": min_stock,
        "使用会社": company,
        "形区分": section,
        "発注日": ""
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

    #商品情報更新（検索機能・更新フォーム・更新チェックあり）
    with update_tab:
        search_button_code("stock_update_search","商品情報更新",data,"update_search_code")
        if "update_search_code" in st.session_state:
            with st.form("stock_update", clear_on_submit=True,enter_to_submit=False):#更新用フォーム
                st.subheader("現在の情報")
                condition=data["資材コード"]==st.session_state["update_search_code"]
                st.dataframe(data.loc[condition,["資材コード", "品名", "型式・寸法", "最低在庫数","使用会社"]],hide_index=True)
                st.subheader("更新情報の入力")
                st.write("※変更しない項目は空欄（最低在庫数は0）のままにしてください")
                up_item=st.text_input("品名")
                up_model=st.text_input("型式・寸法")
                up_min_stock=int(st.number_input("最低在庫数",min_value=0))
                up_company_name=["","A会社","B会社","その他"]
                up_company=st.selectbox("使用会社",up_company_name)
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
                if not up_item and not up_model and not up_min_stock and not up_company: 
                    st.error("いずれかを入力してください")
                if  update_notes:
                    save()
                    st.subheader("今回の更新情報")
                    for update_note in update_notes:#
                        st.write(f"◆{update_note}")
                    st.dataframe(data.loc[condition,[ "資材コード","品名", "型式・寸法", "最低在庫数","使用会社"]],hide_index=True)

    #商品削除（検索機能・削除フォーム・削除チェックあり）
    with delete_tab:
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

    #発注
    with order_tub:
        condition =((data["在庫数"] < data["最低在庫数"]) &
        (data["発注日"].isna()))#isna() は、その値が NaN（欠損値・空欄）かどうかを見る
        already_ordered=data["発注日"].notna()#notna() は、その値が 入ってるかどうかを見る
        if condition.any():#condition(最低在庫数以下の在庫数)の中にTrueが1つでもあるなら
            search_button_code("order_search","発注",data,"order_search_code")
            if "order_search_code" in st.session_state:
                with st.form("order_form",clear_on_submit=True,enter_to_submit=False):
                    st.subheader("現在の情報")
                    order_condition=data["資材コード"]==st.session_state["order_search_code"]
                    st.dataframe(data.loc[order_condition,["資材コード", "品名", "型式・寸法","在庫数","最低在庫数"]],hide_index=True)
                    order_date = st.date_input("発注日", value=date.today())
                    delivery_date = st.date_input("納入予定日 ※未定の場合は空欄のままにしてください", value=None)
                    submitted_order = st.form_submit_button("発注")
                if submitted_order:
                    if not order_date:
                        st.error("発注日を入力してください")
                    elif delivery_date and order_date>delivery_date:
                        st.error("発注日が納入予定日を過ぎています")
                    else:
                        data.loc[order_condition, "発注日"] = str(order_date) #左のままだと文字列ではなくdate 型。
                        if delivery_date:
                            data.loc[order_condition, "納入予定日"] = str(delivery_date)
                        save()
                        st.success("下記の通り、発注されました")
                        st.dataframe(data.loc[order_condition,["資材コード","品名","型式・寸法","発注日","納入予定日"]],hide_index=True)
                        
            st.subheader("⚠️ 発注確認")
            st.markdown(f"<span style='color:red;'>不足している部品が{condition.sum()}個あります、発注してください！</span>",
                unsafe_allow_html=True
            )#unsafe_allow_html=True → HTMLによる色・サイズなどの装飾を許可
            #conditionの中にTrueがいくつあるか（Trueは1　Falseは0　1の合計）
            #lenはTrueとFalseどっちの数も拾うためpandas（表）には使えない
            st.dataframe(data.loc[condition,["資材コード", "品名", "型式・寸法", "在庫数", "最低在庫数"]],hide_index=True)

        else:
            st.caption("✓ 不足している部品（未発注）はありません")

    #発注情報更新（検索機能・変更/検索フォーム・更新チェック（関数）あり）
    with already_ordered_tub:    
        if already_ordered.any():#発注済みにTrueな物が一つでもあれば（発注の時に定義）
            #発注情報更新フォーム(検索あり)
            search_button_code("order_cancel_change_search","発注情報更新",data,"cancel_change_search_code")
            if "cancel_change_search_code" in st.session_state:
                cancel_change_condition = ((data["資材コード"] == st.session_state["cancel_change_search_code"]) &
                (data["発注日"].notna()))#資材コードと一致かつ発注日があるもの
                if cancel_change_condition.any():
                    with st.form("order_cancel_change_form",clear_on_submit=True,enter_to_submit=False):
                        st.subheader("現在の情報")
                        st.dataframe(data.loc[cancel_change_condition].drop(columns=["使用会社","形区分"]),hide_index=True)
                        order_date = st.date_input("発注日", value=None)
                        delivery_date = st.date_input("納入予定日" ,value=None)
                        st.write("※発注取消の場合は空欄のままボタンを押してください")
                        submitted_order_cancel = st.form_submit_button("発注取消")
                        submitted_order_change = st.form_submit_button("発注内容変更")
                        if submitted_order_cancel or submitted_order_change:
                            changed = False
                            if submitted_order_cancel:
                                data.loc[cancel_change_condition, "発注日"] = None
                                data.loc[cancel_change_condition, "納入予定日"] = None
                                changed = True
                                st.success("下記の通り、発注日・納入予定日が取り消されました")
                                
                            elif submitted_order_change:
                                changed=order_change(cancel_change_condition, order_date, delivery_date)
                            if changed:
                                save()
                                st.dataframe(data.loc[cancel_change_condition].drop(columns=["使用会社","形区分"]),hide_index=True)
                else:
                    st.error("この商品は発注されていません")
            st.markdown(
            "<h3><span style='color:green;'>★</span>&nbsp;&nbsp;発注済み商品</h3>",
            unsafe_allow_html=True)
            #span は、文章の一部分だけ色や太さなどを変えたいときに、その範囲を囲むもの
            #<span> ～ </span> <h3> ～ </h3>
            #<h3> ～ </h3> → 全体の文字サイズ
            #<span>★</span> → ★だけ追加で色を変更
            #&nbsp;は空白１個
            st.dataframe(data.loc[already_ordered,["資材コード", "品名", "在庫数","発注日","納入予定日"]],hide_index=True)
            
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
                
                                            

                    

