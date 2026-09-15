import streamlit as st
import sqlite3
from datetime import datetime, date
import os

# データベースが存在しない場合、初回のみ自動作成
if not os.path.exists("disaster_report.db"):
    import init_db

DB_PATH = "disaster_report.db"
IMAGE_DIR = "images"

HQ_PASSWORD = "hq2026"
ADMIN_PASSWORD = "admin2026"

os.makedirs(IMAGE_DIR, exist_ok=True)

st.set_page_config(
    page_title="災害状況報告システム",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==========================
# セッション状態の初期化
# ==========================
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "role" not in st.session_state:
    st.session_state.role = None
if "base_id" not in st.session_state:
    st.session_state.base_id = None
if "base_name" not in st.session_state:
    st.session_state.base_name = None


# ==========================
# DBアクセス関数(共通)
# ==========================
def get_conn():
    return sqlite3.connect(DB_PATH)


def check_base_password(input_password):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "SELECT base_id, base_name FROM bases WHERE base_password = ? AND delete_flag = 0",
        (input_password,)
    )
    result = c.fetchone()
    conn.close()
    return result


def get_companies(base_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "SELECT company_id, company_name, employee_count FROM companies "
        "WHERE base_id = ? AND delete_flag = 0",
        (base_id,)
    )
    result = c.fetchall()
    conn.close()
    return result


def get_places(base_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "SELECT place_id, place_name FROM evacuation_places "
        "WHERE base_id = ? AND delete_flag = 0",
        (base_id,)
    )
    result = c.fetchall()
    conn.close()
    return result


def get_reporters(base_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "SELECT reporter_id, reporter_name FROM reporters "
        "WHERE base_id = ? AND delete_flag = 0",
        (base_id,)
    )
    result = c.fetchall()
    conn.close()
    return result


def save_report(base_id, place_id, report_date, report_time, reporter_id,
                 damage_level, free_comment, detail_rows, image_files):
    conn = get_conn()
    c = conn.cursor()

    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    c.execute("""
        INSERT INTO reports
        (base_id, place_id, report_date, report_time, reporter_id,
         damage_level, free_comment, created_at, delete_flag)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
    """, (base_id, place_id, report_date, report_time, reporter_id,
          damage_level, free_comment, created_at))

    report_id = c.lastrowid

    for row in detail_rows:
        c.execute("""
            INSERT INTO report_details
            (report_id, company_id, total_employee, total_visitor,
             evacuated_employee, evacuated_visitor,
             injured_employee, injured_visitor,
             absent_employee, absent_visitor)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            report_id, row["company_id"],
            row["total_employee"], row["total_visitor"],
            row["evacuated_employee"], row["evacuated_visitor"],
            row["injured_employee"], row["injured_visitor"],
            row["absent_employee"], row["absent_visitor"]
        ))

    for img_path in image_files:
        c.execute("""
            INSERT INTO report_images (report_id, image_path)
            VALUES (?, ?)
        """, (report_id, img_path))

    conn.commit()
    conn.close()
    return report_id


def get_latest_report_per_base(base_id=None):
    conn = get_conn()
    c = conn.cursor()

    if base_id is not None:
        c.execute("""
            SELECT r.report_id, r.base_id, b.base_name, p.place_name,
                   r.report_date, r.report_time, rep.reporter_name,
                   r.damage_level, r.free_comment, r.created_at
            FROM reports r
            JOIN bases b ON r.base_id = b.base_id
            JOIN evacuation_places p ON r.place_id = p.place_id
            JOIN reporters rep ON r.reporter_id = rep.reporter_id
            WHERE r.delete_flag = 0 AND r.base_id = ?
            ORDER BY r.created_at DESC
            LIMIT 1
        """, (base_id,))
    else:
        c.execute("""
            SELECT r.report_id, r.base_id, b.base_name, p.place_name,
                   r.report_date, r.report_time, rep.reporter_name,
                   r.damage_level, r.free_comment, r.created_at
            FROM reports r
            JOIN bases b ON r.base_id = b.base_id
            JOIN evacuation_places p ON r.place_id = p.place_id
            JOIN reporters rep ON r.reporter_id = rep.reporter_id
            WHERE r.delete_flag = 0
            ORDER BY r.created_at DESC
        """)

    rows = c.fetchall()
    conn.close()

    if base_id is not None:
        return rows[0] if rows else None

    latest_map = {}
    for row in rows:
        b_id = row[1]
        if b_id not in latest_map:
            latest_map[b_id] = row
    return list(latest_map.values())


def get_report_history(base_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT r.report_id, r.report_date, r.report_time,
               r.damage_level, rep.reporter_name, r.created_at
        FROM reports r
        JOIN reporters rep ON r.reporter_id = rep.reporter_id
        WHERE r.delete_flag = 0 AND r.base_id = ?
        ORDER BY r.created_at DESC
    """, (base_id,))
    rows = c.fetchall()
    conn.close()
    return rows


def get_report_details(report_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT rd.company_id, c.company_name,
               rd.total_employee, rd.total_visitor,
               rd.evacuated_employee, rd.evacuated_visitor,
               rd.injured_employee, rd.injured_visitor,
               rd.absent_employee, rd.absent_visitor
        FROM report_details rd
        JOIN companies c ON rd.company_id = c.company_id
        WHERE rd.report_id = ?
    """, (report_id,))
    rows = c.fetchall()
    conn.close()
    return rows


def get_report_images(report_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT image_path FROM report_images WHERE report_id = ?", (report_id,))
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]


def get_report_free_comment(report_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT free_comment FROM reports WHERE report_id = ?", (report_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else ""


def get_report_row_by_id(report_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT r.report_id, r.base_id, b.base_name, p.place_name,
               r.report_date, r.report_time, rep.reporter_name,
               r.damage_level, r.free_comment, r.created_at
        FROM reports r
        JOIN bases b ON r.base_id = b.base_id
        JOIN evacuation_places p ON r.place_id = p.place_id
        JOIN reporters rep ON r.reporter_id = rep.reporter_id
        WHERE r.report_id = ?
    """, (report_id,))
    row = c.fetchone()
    conn.close()
    return row


# ==========================
# 管理者用:マスタCRUD関数
# ==========================
def get_all_bases_admin():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT base_id, base_name, base_password FROM bases WHERE delete_flag = 0")
    rows = c.fetchall()
    conn.close()
    return rows


def add_base(base_name, base_password):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO bases (base_name, base_password, delete_flag) VALUES (?, ?, 0)",
        (base_name, base_password)
    )
    conn.commit()
    conn.close()


def update_base(base_id, base_name, base_password):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "UPDATE bases SET base_name = ?, base_password = ? WHERE base_id = ?",
        (base_name, base_password, base_id)
    )
    conn.commit()
    conn.close()


def delete_base(base_id, deleted_by="admin"):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "UPDATE bases SET delete_flag = 1, delete_datetime = ?, delete_by = ? WHERE base_id = ?",
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), deleted_by, base_id)
    )
    conn.commit()
    conn.close()


def get_all_companies_admin(base_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "SELECT company_id, company_name, employee_count FROM companies "
        "WHERE base_id = ? AND delete_flag = 0",
        (base_id,)
    )
    rows = c.fetchall()
    conn.close()
    return rows


def add_company(base_id, company_name, employee_count):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO companies (base_id, company_name, employee_count, delete_flag) VALUES (?, ?, ?, 0)",
        (base_id, company_name, employee_count)
    )
    conn.commit()
    conn.close()


def update_company(company_id, company_name, employee_count):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "UPDATE companies SET company_name = ?, employee_count = ? WHERE company_id = ?",
        (company_name, employee_count, company_id)
    )
    conn.commit()
    conn.close()


def delete_company(company_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE companies SET delete_flag = 1 WHERE company_id = ?", (company_id,))
    conn.commit()
    conn.close()


def get_all_places_admin(base_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "SELECT place_id, place_name FROM evacuation_places "
        "WHERE base_id = ? AND delete_flag = 0",
        (base_id,)
    )
    rows = c.fetchall()
    conn.close()
    return rows


def add_place(base_id, place_name):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO evacuation_places (base_id, place_name, delete_flag) VALUES (?, ?, 0)",
        (base_id, place_name)
    )
    conn.commit()
    conn.close()


def update_place(place_id, place_name):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE evacuation_places SET place_name = ? WHERE place_id = ?", (place_name, place_id))
    conn.commit()
    conn.close()


def delete_place(place_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE evacuation_places SET delete_flag = 1 WHERE place_id = ?", (place_id,))
    conn.commit()
    conn.close()


def get_all_reporters_admin(base_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "SELECT reporter_id, reporter_name FROM reporters "
        "WHERE base_id = ? AND delete_flag = 0",
        (base_id,)
    )
    rows = c.fetchall()
    conn.close()
    return rows


def add_reporter(base_id, reporter_name):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO reporters (base_id, reporter_name, delete_flag) VALUES (?, ?, 0)",
        (base_id, reporter_name)
    )
    conn.commit()
    conn.close()


def update_reporter(reporter_id, reporter_name):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE reporters SET reporter_name = ? WHERE reporter_id = ?", (reporter_name, reporter_id))
    conn.commit()
    conn.close()


def delete_reporter(reporter_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE reporters SET delete_flag = 1 WHERE reporter_id = ?", (reporter_id,))
    conn.commit()
    conn.close()


# ==========================
# 管理者用:報告データ削除・復元
# ==========================
def get_active_reports_by_base(base_id):
    """指定拠点の、未削除の報告一覧を返す"""
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT r.report_id, r.report_date, r.report_time,
               r.damage_level, rep.reporter_name
        FROM reports r
        JOIN reporters rep ON r.reporter_id = rep.reporter_id
        WHERE r.base_id = ? AND r.delete_flag = 0
        ORDER BY r.created_at DESC
    """, (base_id,))
    rows = c.fetchall()
    conn.close()
    return rows


def get_deleted_reports_by_base(base_id):
    """指定拠点の、削除済みの報告一覧を返す"""
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT r.report_id, r.report_date, r.report_time,
               r.damage_level, rep.reporter_name,
               r.delete_datetime, r.delete_by
        FROM reports r
        JOIN reporters rep ON r.reporter_id = rep.reporter_id
        WHERE r.base_id = ? AND r.delete_flag = 1
        ORDER BY r.delete_datetime DESC
    """, (base_id,))
    rows = c.fetchall()
    conn.close()
    return rows


def delete_report(report_id, deleted_by="admin"):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "UPDATE reports SET delete_flag = 1, delete_datetime = ?, delete_by = ? WHERE report_id = ?",
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), deleted_by, report_id)
    )
    conn.commit()
    conn.close()


def restore_report(report_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "UPDATE reports SET delete_flag = 0, delete_datetime = NULL, delete_by = NULL WHERE report_id = ?",
        (report_id,)
    )
    conn.commit()
    conn.close()


# ==========================
# 表示用ヘルパー
# ==========================
def damage_level_color(level):
    colors = {
        "甚大": "#ff4d4d",
        "重大": "#ff9999",
        "中程度": "#fff3b0",
        "軽微": "#e6f4ea",
        "被害なし": "#f0f0f0",
    }
    return colors.get(level, "#f0f0f0")


def display_report_card(report_row, show_details=True, show_images=True):
    (report_id, base_id, base_name, place_name,
     report_date, report_time, reporter_name,
     damage_level, free_comment, created_at) = report_row

    bg_color = damage_level_color(damage_level)

    st.markdown(
        f"""
        <div style="background-color:{bg_color}; padding:15px; border-radius:8px; margin-bottom:10px;">
        <h4 style="margin:0;">拠点:{base_name}　被害レベル:【{damage_level}】</h4>
        <p style="margin:5px 0 0 0;">
        避難場所:{place_name}　報告日時:{report_date} {report_time}　報告者:{reporter_name}
        </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    details = get_report_details(report_id)

    total_emp = sum(d[2] for d in details)
    total_vis = sum(d[3] for d in details)
    evac_emp = sum(d[4] for d in details)
    evac_vis = sum(d[5] for d in details)
    inj_emp = sum(d[6] for d in details)
    inj_vis = sum(d[7] for d in details)
    abs_emp = sum(d[8] for d in details)
    abs_vis = sum(d[9] for d in details)
    unconf_emp = total_emp - evac_emp - abs_emp
    unconf_vis = total_vis - evac_vis - abs_vis

    st.markdown(" **【拠点合計】** ")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("在籍合計", f"{total_emp + total_vis}名", f"社員{total_emp}/来客{total_vis}")
    col2.metric("避難合計", f"{evac_emp + evac_vis}名", f"うち負傷{inj_emp + inj_vis}")
    col3.metric("不在合計", f"{abs_emp + abs_vis}名")
    col4.metric("未確認合計", f"{unconf_emp + unconf_vis}名")

    if show_details:
        st.markdown(" **【内訳】** ")
        for d in details:
            (company_id, company_name, t_emp, t_vis, e_emp, e_vis,
             i_emp, i_vis, a_emp, a_vis) = d
            u_emp = t_emp - e_emp - a_emp
            u_vis = t_vis - e_vis - a_vis
            st.write(
                f"▼ {company_name}　"
                f"在籍:{t_emp + t_vis}(社員{t_emp}/来客{t_vis})　"
                f"避難:{e_emp + e_vis}(うち負傷{i_emp + i_vis})　"
                f"不在:{a_emp + a_vis}　"
                f"未確認:{u_emp + u_vis}"
            )

    comment = get_report_free_comment(report_id)
    if comment:
        st.markdown(" **【状況詳細】** ")
        st.write(comment)

    if show_images:
        images = get_report_images(report_id)
        if images:
            st.markdown(" **【添付画像】** ")
            cols = st.columns(len(images))
            for i, img_path in enumerate(images):
                if os.path.exists(img_path):
                    cols[i].image(img_path, use_container_width=True)


# ==========================
# 拠点担当者:新規報告フォーム
# ==========================
def show_new_report_form(base_id, base_name):
    st.subheader("新規報告入力")

    companies = get_companies(base_id)
    places = get_places(base_id)
    reporters = get_reporters(base_id)

    if not companies or not places or not reporters:
        st.warning("マスタデータが未登録です。管理者に確認してください。")
        return

    col1, col2 = st.columns(2)
    with col1:
        report_date = st.date_input("避難年月日", value=date.today())
    with col2:
        report_time = st.time_input("報告時刻", value=datetime.now().time())

    place_dict = {name: pid for pid, name in places}
    place_name = st.selectbox("避難場所", list(place_dict.keys()))

    reporter_dict = {name: rid for rid, name in reporters}
    reporter_name = st.selectbox("報告者", list(reporter_dict.keys()))

    damage_level = st.selectbox(
        "被害レベル",
        ["被害なし", "軽微", "中程度", "重大", "甚大"]
    )

    st.divider()
    st.markdown("### 会社部署ごとの人数内訳")

    detail_rows = []

    for company_id, company_name, employee_count in companies:
        with st.expander(f"■ {company_name}", expanded=True):
            c1, c2 = st.columns(2)
            with c1:
                total_employee = st.number_input(
                    f"在籍総員数(社員)_{company_name}",
                    min_value=0, value=employee_count, key=f"total_emp_{company_id}"
                )
            with c2:
                total_visitor = st.number_input(
                    f"在籍総員数(来客)_{company_name}",
                    min_value=0, value=0, key=f"total_vis_{company_id}"
                )

            c3, c4 = st.columns(2)
            with c3:
                evacuated_employee = st.number_input(
                    f"避難員数(社員)_{company_name}",
                    min_value=0, value=0, key=f"evac_emp_{company_id}"
                )
                injured_employee = st.number_input(
                    f"　うち負傷者(社員)_{company_name}",
                    min_value=0, value=0, key=f"inj_emp_{company_id}"
                )
            with c4:
                evacuated_visitor = st.number_input(
                    f"避難員数(来客)_{company_name}",
                    min_value=0, value=0, key=f"evac_vis_{company_id}"
                )
                injured_visitor = st.number_input(
                    f"　うち負傷者(来客)_{company_name}",
                    min_value=0, value=0, key=f"inj_vis_{company_id}"
                )

            c5, c6 = st.columns(2)
            with c5:
                absent_employee = st.number_input(
                    f"不在員数(社員)_{company_name}",
                    min_value=0, value=0, key=f"abs_emp_{company_id}"
                )
            with c6:
                absent_visitor = st.number_input(
                    f"不在員数(来客)_{company_name}",
                    min_value=0, value=0, key=f"abs_vis_{company_id}"
                )

            if injured_employee > evacuated_employee:
                st.error(f"{company_name}:社員のうち負傷者数が避難員数を超えています")
            if injured_visitor > evacuated_visitor:
                st.error(f"{company_name}:来客のうち負傷者数が避難員数を超えています")

            unconfirmed_employee = total_employee - evacuated_employee - absent_employee
            unconfirmed_visitor = total_visitor - evacuated_visitor - absent_visitor

            st.info(
                f"未確認人数(社員):{unconfirmed_employee}名　"
                f"未確認人数(来客):{unconfirmed_visitor}名"
            )

            detail_rows.append({
                "company_id": company_id,
                "total_employee": total_employee,
                "total_visitor": total_visitor,
                "evacuated_employee": evacuated_employee,
                "evacuated_visitor": evacuated_visitor,
                "injured_employee": injured_employee,
                "injured_visitor": injured_visitor,
                "absent_employee": absent_employee,
                "absent_visitor": absent_visitor,
            })

    st.divider()

    free_comment = st.text_area("状況詳細(自由記述、300文字以内)", max_chars=300, height=150)
    st.caption(f"{len(free_comment)} / 300文字")

    uploaded_images = st.file_uploader(
        "画像添付(最大3枚)",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True
    )

    if uploaded_images and len(uploaded_images) > 3:
        st.error("画像は最大3枚までです。3枚以内にしてください。")

    st.divider()

    if st.button("この内容で報告する", type="primary"):
        error_flag = False

        for row in detail_rows:
            if row["injured_employee"] > row["evacuated_employee"]:
                error_flag = True
            if row["injured_visitor"] > row["evacuated_visitor"]:
                error_flag = True

        if uploaded_images and len(uploaded_images) > 3:
            error_flag = True

        if error_flag:
            st.error("入力内容にエラーがあります。上記の項目を確認してください。")
        else:
            saved_image_paths = []
            if uploaded_images:
                for img in uploaded_images:
                    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
                    save_path = os.path.join(IMAGE_DIR, f"{timestamp}_{img.name}")
                    with open(save_path, "wb") as f:
                        f.write(img.getbuffer())
                    saved_image_paths.append(save_path)

            report_id = save_report(
                base_id=base_id,
                place_id=place_dict[place_name],
                report_date=str(report_date),
                report_time=report_time.strftime("%H:%M"),
                reporter_id=reporter_dict[reporter_name],
                damage_level=damage_level,
                free_comment=free_comment,
                detail_rows=detail_rows,
                image_files=saved_image_paths
            )

            st.success(f"報告を送信しました(報告ID:{report_id})")
            st.balloons()


# ==========================
# 拠点担当者:自拠点の状況タブ
# ==========================
def show_own_base_status(base_id):
    st.subheader("自拠点の最新状況")

    latest = get_latest_report_per_base(base_id=base_id)

    if latest is None:
        st.info("まだ報告がありません。")
        return

    display_report_card(latest, show_details=True, show_images=True)


# ==========================
# 拠点担当者:報告履歴タブ
# ==========================
def show_own_base_history(base_id):
    st.subheader("自拠点の報告履歴")

    history = get_report_history(base_id)

    if not history:
        st.info("まだ報告履歴がありません。")
        return

    options = {}
    for row in history:
        report_id, report_date, report_time, damage_level, reporter_name, created_at = row
        label = f"{report_date} {report_time}(報告者:{reporter_name}/被害レベル:{damage_level})"
        options[label] = report_id

    selected_label = st.selectbox(
        "確認したい報告を選択してください", list(options.keys()), key=f"history_select_{base_id}"
    )
    selected_report_id = options[selected_label]

    report_row = get_report_row_by_id(selected_report_id)

    st.divider()
    display_report_card(report_row, show_details=True, show_images=True)


# ==========================
# 本部担当者:全拠点最新報告一覧
# ==========================
def show_hq_dashboard():
    st.subheader("全拠点 最新報告一覧")

    latest_list = get_latest_report_per_base()

    if not latest_list:
        st.info("まだ報告がありません。")
        return

    priority = {"甚大": 0, "重大": 1, "中程度": 2, "軽微": 3, "被害なし": 4}
    latest_list.sort(key=lambda row: priority.get(row[7], 5))

    for report_row in latest_list:
        with st.container():
            display_report_card(report_row, show_details=True, show_images=True)
        st.divider()


def show_hq_history_search():
    st.subheader("拠点別 報告履歴検索")

    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT base_id, base_name FROM bases WHERE delete_flag = 0")
    bases = c.fetchall()
    conn.close()

    base_dict = {name: bid for bid, name in bases}
    selected_base_name = st.selectbox(
        "拠点を選択してください", list(base_dict.keys()), key="hq_history_base_select"
    )
    selected_base_id = base_dict[selected_base_name]

    show_own_base_history(selected_base_id)


# ==========================
# 管理者:拠点マスタ管理
# ==========================
def show_admin_bases():
    st.subheader("拠点マスタ管理")

    st.markdown("### 新規拠点の追加")
    with st.form("add_base_form"):
        new_base_name = st.text_input("拠点名")
        new_base_password = st.text_input("拠点パスワード")
        submitted = st.form_submit_button("追加する")
        if submitted:
            if new_base_name and new_base_password:
                add_base(new_base_name, new_base_password)
                st.success(f"拠点「{new_base_name}」を追加しました")
                st.rerun()
            else:
                st.error("拠点名とパスワードを入力してください")

    st.divider()
    st.markdown("### 既存拠点の編集・削除")

    bases = get_all_bases_admin()
    for base_id, base_name, base_password in bases:
        with st.expander(f"■ {base_name}"):
            edit_name = st.text_input("拠点名", value=base_name, key=f"base_name_{base_id}")
            edit_password = st.text_input(
                "拠点パスワード", value=base_password, key=f"base_pw_{base_id}"
            )

            col1, col2 = st.columns(2)
            with col1:
                if st.button("更新する", key=f"update_base_{base_id}"):
                    update_base(base_id, edit_name, edit_password)
                    st.success("更新しました")
                    st.rerun()
            with col2:
                if st.button("削除する", key=f"delete_base_{base_id}", type="secondary"):
                    delete_base(base_id)
                    st.warning(f"拠点「{base_name}」を削除しました")
                    st.rerun()


# ==========================
# 管理者:会社部署マスタ管理
# ==========================
def show_admin_companies():
    st.subheader("会社部署マスタ管理")

    bases = get_all_bases_admin()
    base_dict = {name: bid for bid, name, pw in bases}
    selected_base_name = st.selectbox("対象拠点を選択", list(base_dict.keys()), key="company_base_select")
    selected_base_id = base_dict[selected_base_name]

    st.markdown("### 新規会社部署の追加")
    with st.form("add_company_form"):
        new_company_name = st.text_input("会社部署名")
        new_employee_count = st.number_input("社員数", min_value=0, value=0)
        submitted = st.form_submit_button("追加する")
        if submitted:
            if new_company_name:
                add_company(selected_base_id, new_company_name, new_employee_count)
                st.success(f"会社部署「{new_company_name}」を追加しました")
                st.rerun()
            else:
                st.error("会社部署名を入力してください")

    st.divider()
    st.markdown("### 既存会社部署の編集・削除")

    companies = get_all_companies_admin(selected_base_id)
    for company_id, company_name, employee_count in companies:
        with st.expander(f"■ {company_name}"):
            edit_name = st.text_input("会社部署名", value=company_name, key=f"comp_name_{company_id}")
            edit_count = st.number_input(
                "社員数", min_value=0, value=employee_count, key=f"comp_count_{company_id}"
            )

            col1, col2 = st.columns(2)
            with col1:
                if st.button("更新する", key=f"update_comp_{company_id}"):
                    update_company(company_id, edit_name, edit_count)
                    st.success("更新しました")
                    st.rerun()
            with col2:
                if st.button("削除する", key=f"delete_comp_{company_id}", type="secondary"):
                    delete_company(company_id)
                    st.warning(f"会社部署「{company_name}」を削除しました")
                    st.rerun()


# ==========================
# 管理者:避難場所マスタ管理
# ==========================
def show_admin_places():
    st.subheader("避難場所マスタ管理")

    bases = get_all_bases_admin()
    base_dict = {name: bid for bid, name, pw in bases}
    selected_base_name = st.selectbox("対象拠点を選択", list(base_dict.keys()), key="place_base_select")
    selected_base_id = base_dict[selected_base_name]

    st.markdown("### 新規避難場所の追加")
    with st.form("add_place_form"):
        new_place_name = st.text_input("避難場所名")
        submitted = st.form_submit_button("追加する")
        if submitted:
            if new_place_name:
                add_place(selected_base_id, new_place_name)
                st.success(f"避難場所「{new_place_name}」を追加しました")
                st.rerun()
            else:
                st.error("避難場所名を入力してください")

    st.divider()
    st.markdown("### 既存避難場所の編集・削除")

    places = get_all_places_admin(selected_base_id)
    for place_id, place_name in places:
        with st.expander(f"■ {place_name}"):
            edit_name = st.text_input("避難場所名", value=place_name, key=f"place_name_{place_id}")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("更新する", key=f"update_place_{place_id}"):
                    update_place(place_id, edit_name)
                    st.success("更新しました")
                    st.rerun()
            with col2:
                if st.button("削除する", key=f"delete_place_{place_id}", type="secondary"):
                    delete_place(place_id)
                    st.warning(f"避難場所「{place_name}」を削除しました")
                    st.rerun()


# ==========================
# 管理者:報告者マスタ管理
# ==========================
def show_admin_reporters():
    st.subheader("報告者マスタ管理")

    bases = get_all_bases_admin()
    base_dict = {name: bid for bid, name, pw in bases}
    selected_base_name = st.selectbox("対象拠点を選択", list(base_dict.keys()), key="reporter_base_select")
    selected_base_id = base_dict[selected_base_name]

    st.markdown("### 新規報告者の追加")
    with st.form("add_reporter_form"):
        new_reporter_name = st.text_input("報告者名")
        submitted = st.form_submit_button("追加する")
        if submitted:
            if new_reporter_name:
                add_reporter(selected_base_id, new_reporter_name)
                st.success(f"報告者「{new_reporter_name}」を追加しました")
                st.rerun()
            else:
                st.error("報告者名を入力してください")

    st.divider()
    st.markdown("### 既存報告者の編集・削除")

    reporters = get_all_reporters_admin(selected_base_id)
    for reporter_id, reporter_name in reporters:
        with st.expander(f"■ {reporter_name}"):
            edit_name = st.text_input("報告者名", value=reporter_name, key=f"reporter_name_{reporter_id}")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("更新する", key=f"update_reporter_{reporter_id}"):
                    update_reporter(reporter_id, edit_name)
                    st.success("更新しました")
                    st.rerun()
            with col2:
                if st.button("削除する", key=f"delete_reporter_{reporter_id}", type="secondary"):
                    delete_reporter(reporter_id)
                    st.warning(f"報告者「{reporter_name}」を削除しました")
                    st.rerun()


# ==========================
# 管理者:報告データの削除・復元
# ==========================
def show_admin_report_deletion():
    st.subheader("報告データの削除・復元")

    bases = get_all_bases_admin()
    base_dict = {name: bid for bid, name, pw in bases}
    selected_base_name = st.selectbox(
        "対象拠点を選択", list(base_dict.keys()), key="report_del_base_select"
    )
    selected_base_id = base_dict[selected_base_name]

    tab_active, tab_deleted = st.tabs(["有効な報告(削除する)", "削除済み報告(復元する)"])

    # ---- 有効な報告の削除 ----
    with tab_active:
        active_reports = get_active_reports_by_base(selected_base_id)

        if not active_reports:
            st.info("この拠点には有効な報告がありません。")
        else:
            options = {}
            for row in active_reports:
                report_id, report_date, report_time, damage_level, reporter_name = row
                label = f"{report_date} {report_time}(報告者:{reporter_name}/被害レベル:{damage_level})"
                options[label] = report_id

            selected_label = st.selectbox(
                "削除したい報告を選択してください",
                list(options.keys()),
                key="delete_report_select"
            )
            selected_report_id = options[selected_label]

            st.markdown("#### 選択した報告の内容")
            report_row = get_report_row_by_id(selected_report_id)
            display_report_card(report_row, show_details=True, show_images=True)

            st.warning("この操作は取り消せますが、慎重に行ってください。")
            confirm = st.checkbox("内容を確認しました。この報告を削除します。", key="delete_confirm")

            if st.button("この報告を削除する", type="primary", disabled=not confirm):
                delete_report(selected_report_id, deleted_by="admin")
                st.success("報告を削除しました(復元は「削除済み報告」タブから可能です)")
                st.rerun()

    # ---- 削除済み報告の復元 ----
    with tab_deleted:
        deleted_reports = get_deleted_reports_by_base(selected_base_id)

        if not deleted_reports:
            st.info("この拠点には削除済みの報告がありません。")
        else:
            for row in deleted_reports:
                (report_id, report_date, report_time, damage_level,
                 reporter_name, delete_datetime, delete_by) = row

                with st.expander(
                    f"■ {report_date} {report_time}(報告者:{reporter_name}/"
                    f"被害レベル:{damage_level})"
                ):
                    st.write(f"削除日時:{delete_datetime}　削除者:{delete_by}")

                    report_row = get_report_row_by_id(report_id)
                    display_report_card(report_row, show_details=True, show_images=True)

                    if st.button("この報告を復元する", key=f"restore_{report_id}"):
                        restore_report(report_id)
                        st.success("報告を復元しました")
                        st.rerun()


# ==========================
# ログイン画面
# ==========================
def login_screen():
    st.title("災害状況報告システム ログイン")

    role_choice = st.radio(
        "ログイン種別を選択してください",
        ["拠点担当者", "本部担当者", "管理者"]
    )
    password = st.text_input("パスワードを入力してください", type="password")

    if st.button("ログイン"):
        if role_choice == "拠点担当者":
            result = check_base_password(password)
            if result:
                base_id, base_name = result
                st.session_state.authenticated = True
                st.session_state.role = "base"
                st.session_state.base_id = base_id
                st.session_state.base_name = base_name
                st.rerun()
            else:
                st.error("パスワードが正しくありません")

        elif role_choice == "本部担当者":
            if password == HQ_PASSWORD:
                st.session_state.authenticated = True
                st.session_state.role = "hq"
                st.rerun()
            else:
                st.error("パスワードが正しくありません")

        elif role_choice == "管理者":
            if password == ADMIN_PASSWORD:
                st.session_state.authenticated = True
                st.session_state.role = "admin"
                st.rerun()
            else:
                st.error("パスワードが正しくありません")


def logout_button():
    if st.sidebar.button("ログアウト"):
        st.session_state.authenticated = False
        st.session_state.role = None
        st.session_state.base_id = None
        st.session_state.base_name = None
        st.rerun()


# ==========================
# メイン処理
# ==========================
if not st.session_state.authenticated:
    login_screen()
else:
    logout_button()

    if st.session_state.role == "base":
        st.title(f"拠点担当者ページ:{st.session_state.base_name}")

        tab1, tab2, tab3 = st.tabs(["新規報告", "自拠点の状況", "報告履歴"])

        with tab1:
            show_new_report_form(st.session_state.base_id, st.session_state.base_name)

        with tab2:
            show_own_base_status(st.session_state.base_id)

        with tab3:
            show_own_base_history(st.session_state.base_id)

    elif st.session_state.role == "hq":
        st.title("本部担当者ページ")

        tab1, tab2 = st.tabs(["最新報告一覧", "拠点別履歴検索"])

        with tab1:
            show_hq_dashboard()

        with tab2:
            show_hq_history_search()

    elif st.session_state.role == "admin":
        st.title("管理者ページ")

        tab1, tab2, tab3, tab4, tab5 = st.tabs(
            ["拠点マスタ", "会社部署マスタ", "避難場所マスタ", "報告者マスタ", "報告データ削除"]
        )

        with tab1:
            show_admin_bases()

        with tab2:
            show_admin_companies()

        with tab3:
            show_admin_places()

        with tab4:
            show_admin_reporters()

        with tab5:
            show_admin_report_deletion()
