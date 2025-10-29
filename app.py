from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "secretkey"


# =========================
# 📦 قاعدة البيانات
# =========================
DB_PATH = os.environ.get("DB_PATH") or os.path.join("database", "farm.db") if os.path.isdir("database") else "poultry.db"


def get_db():
    # Ensure directory exists if using nested path
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()

    # جدول الدفعات
    c.execute('''CREATE TABLE IF NOT EXISTS batches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        breed TEXT NOT NULL,
        start_date TEXT NOT NULL,
        initial_count INTEGER NOT NULL,
        chick_price REAL DEFAULT 0
    )''')

    # جدول العلف
    c.execute('''CREATE TABLE IF NOT EXISTS feed (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        batch_id INTEGER,
        date TEXT,
        feed_type TEXT,
        quantity REAL,
        price REAL,
        FOREIGN KEY(batch_id) REFERENCES batches(id)
    )''')

    # جدول الأدوية
    c.execute('''CREATE TABLE IF NOT EXISTS medications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        batch_id INTEGER,
        date TEXT,
        name TEXT,
        purpose TEXT,
        price REAL,
        FOREIGN KEY(batch_id) REFERENCES batches(id)
    )''')

    # جدول المصروفات الإضافية
    c.execute('''CREATE TABLE IF NOT EXISTS extra_expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        batch_id INTEGER,
        date TEXT,
        name TEXT,
        price REAL,
        FOREIGN KEY(batch_id) REFERENCES batches(id)
    )''')

    # جدول النافق اليومي
    c.execute('''CREATE TABLE IF NOT EXISTS mortality (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        batch_id INTEGER,
        date TEXT,
        count INTEGER,
        note TEXT,
        FOREIGN KEY(batch_id) REFERENCES batches(id)
    )''')

    # جدول المبيعات الفعلية
    c.execute('''CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        batch_id INTEGER,
        date TEXT,
        quantity INTEGER,
        average_weight_kg REAL,
        price_per_kg REAL,
        total_weight_kg REAL,
        total_price REAL,
        note TEXT,
        FOREIGN KEY(batch_id) REFERENCES batches(id)
    )''')

    conn.commit()
    conn.close()


# =========================
# 🏠 الصفحة الرئيسية
# =========================
@app.route("/")
def index():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM batches")
    batches = c.fetchall()

    # Dashboard quick stats
    c.execute("SELECT COUNT(*) FROM batches")
    total_batches = c.fetchone()[0] or 0

    c.execute("SELECT COALESCE(SUM(initial_count),0) FROM batches")
    total_chicks = c.fetchone()[0] or 0

    # Expenses = chicks + feed + meds + extras
    c.execute("SELECT COALESCE(SUM(chick_price * initial_count),0) FROM batches")
    total_chicks_cost = c.fetchone()[0] or 0

    c.execute("SELECT COALESCE(SUM(price),0) FROM feed")
    total_feed = c.fetchone()[0] or 0

    c.execute("SELECT COALESCE(SUM(price),0) FROM medications")
    total_meds = c.fetchone()[0] or 0

    c.execute("SELECT COALESCE(SUM(price),0) FROM extra_expenses")
    total_extras = c.fetchone()[0] or 0

    total_expenses = (total_chicks_cost or 0) + (total_feed or 0) + (total_meds or 0) + (total_extras or 0)
    conn.close()
    return render_template(
        "index.html",
        batches=batches,
        total_batches=total_batches,
        total_chicks=total_chicks,
        total_expenses=total_expenses,
    )


# =========================
# ➕ إضافة دفعة جديدة
# =========================
@app.route("/batches/add", methods=["GET", "POST"])
def add_batch():
    if request.method == "POST":
        name = request.form["name"]
        breed = request.form["breed"]
        start_date = request.form["start_date"]
        initial_count = int(request.form["initial_count"])
        chick_price = float(request.form["chick_price"])

        conn = get_db()
        c = conn.cursor()
        c.execute(
            "INSERT INTO batches (name, breed, start_date, initial_count, chick_price) VALUES (?, ?, ?, ?, ?)",
            (name, breed, start_date, initial_count, chick_price),
        )
        conn.commit()
        conn.close()

        flash("✅ تمت إضافة الدفعة بنجاح", "success")
        return redirect(url_for("index"))

    return render_template("add_batch.html")


# =========================
# 📋 عرض تفاصيل دفعة
# =========================
@app.route("/batch/<int:batch_id>")
def view_batch(batch_id):
    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT * FROM batches WHERE id = ?", (batch_id,))
    batch = c.fetchone()

    c.execute("SELECT * FROM feed WHERE batch_id = ?", (batch_id,))
    feeds = c.fetchall()

    c.execute("SELECT * FROM medications WHERE batch_id = ?", (batch_id,))
    meds = c.fetchall()

    c.execute("SELECT * FROM extra_expenses WHERE batch_id = ?", (batch_id,))
    extras = c.fetchall()

    c.execute("SELECT * FROM mortality WHERE batch_id = ? ORDER BY date DESC, id DESC", (batch_id,))
    mortalities = c.fetchall()

    c.execute("SELECT * FROM sales WHERE batch_id = ? ORDER BY date DESC, id DESC", (batch_id,))
    sales = c.fetchall()

    conn.close()
    return render_template(
        "view_batch.html",
        batch=batch,
        feeds=feeds,
        meds=meds,
        extras=extras,
        mortalities=mortalities,
        sales=sales
    )


# =========================
# ➕ إضافة علف
# =========================
@app.route("/feed/add/<int:batch_id>", methods=["GET", "POST"])
def add_feed(batch_id):
    if request.method == "POST":
        date = request.form["date"]
        feed_type = request.form["feed_type"]
        quantity = float(request.form["quantity"])
        price = float(request.form["price"])

        conn = get_db()
        c = conn.cursor()
        c.execute(
            "INSERT INTO feed (batch_id, date, feed_type, quantity, price) VALUES (?, ?, ?, ?, ?)",
            (batch_id, date, feed_type, quantity, price),
        )
        conn.commit()
        conn.close()

        flash("✅ تمت إضافة العلف", "success")
        return redirect(url_for("view_batch", batch_id=batch_id))

    return render_template("add_feed.html", batch_id=batch_id)


@app.route("/feed/edit/<int:id>/<int:batch_id>", methods=["GET", "POST"])
def edit_feed(id, batch_id):
    conn = get_db()
    c = conn.cursor()
    if request.method == "POST":
        date = request.form["date"]
        feed_type = request.form["feed_type"]
        quantity = float(request.form["quantity"]) if request.form.get("quantity") else 0
        price = float(request.form["price"]) if request.form.get("price") else 0
        c.execute("UPDATE feed SET date=?, feed_type=?, quantity=?, price=? WHERE id=?", (date, feed_type, quantity, price, id))
        conn.commit()
        conn.close()
        flash("✅ تم تحديث سجل العلف", "success")
        return redirect(url_for("view_batch", batch_id=batch_id))
    c.execute("SELECT * FROM feed WHERE id=?", (id,))
    rec = c.fetchone()
    conn.close()
    return render_template("edit_feed.html", record=rec, batch_id=batch_id)

# =========================
# ➕ إضافة دواء
# =========================
@app.route("/med/add/<int:batch_id>", methods=["GET", "POST"])
def add_med(batch_id):
    if request.method == "POST":
        date = request.form["date"]
        name = request.form["name"]
        purpose = request.form["purpose"]
        price = float(request.form["price"])

        conn = get_db()
        c = conn.cursor()
        c.execute(
            "INSERT INTO medications (batch_id, date, name, purpose, price) VALUES (?, ?, ?, ?, ?)",
            (batch_id, date, name, purpose, price),
        )
        conn.commit()
        conn.close()

        flash("✅ تمت إضافة الدواء", "success")
        return redirect(url_for("view_batch", batch_id=batch_id))

    return render_template("add_med.html", batch_id=batch_id)


@app.route("/med/edit/<int:id>/<int:batch_id>", methods=["GET", "POST"])
def edit_med(id, batch_id):
    conn = get_db()
    c = conn.cursor()
    if request.method == "POST":
        date = request.form["date"]
        name = request.form["name"]
        purpose = request.form["purpose"]
        price = float(request.form["price"]) if request.form.get("price") else 0
        c.execute("UPDATE medications SET date=?, name=?, purpose=?, price=? WHERE id=?", (date, name, purpose, price, id))
        conn.commit()
        conn.close()
        flash("✅ تم تحديث سجل الدواء", "success")
        return redirect(url_for("view_batch", batch_id=batch_id))
    c.execute("SELECT * FROM medications WHERE id=?", (id,))
    rec = c.fetchone()
    conn.close()
    return render_template("edit_med.html", record=rec, batch_id=batch_id)

# =========================
# ➕ إضافة مصروف إضافي
# =========================
@app.route("/extra/add/<int:batch_id>", methods=["GET", "POST"])
def add_extra(batch_id):
    if request.method == "POST":
        date = request.form["date"]
        name = request.form["name"]
        price = float(request.form["price"])

        conn = get_db()
        c = conn.cursor()
        c.execute(
            "INSERT INTO extra_expenses (batch_id, date, name, price) VALUES (?, ?, ?, ?)",
            (batch_id, date, name, price),
        )
        conn.commit()
        conn.close()

        flash("✅ تمت إضافة المصروف", "success")
        return redirect(url_for("view_batch", batch_id=batch_id))

    return render_template("add_extra.html", batch_id=batch_id)


@app.route("/extra/edit/<int:id>/<int:batch_id>", methods=["GET", "POST"])
def edit_extra(id, batch_id):
    conn = get_db()
    c = conn.cursor()
    if request.method == "POST":
        date = request.form["date"]
        name = request.form["name"]
        price = float(request.form["price"]) if request.form.get("price") else 0
        c.execute("UPDATE extra_expenses SET date=?, name=?, price=? WHERE id=?", (date, name, price, id))
        conn.commit()
        conn.close()
        flash("✅ تم تحديث المصروف", "success")
        return redirect(url_for("view_batch", batch_id=batch_id))
    c.execute("SELECT * FROM extra_expenses WHERE id=?", (id,))
    rec = c.fetchone()
    conn.close()
    return render_template("edit_extra.html", record=rec, batch_id=batch_id)

# =========================
# ❌ حذف الدفعة
# =========================
@app.route("/batch/delete/<int:batch_id>")
def delete_batch(batch_id):
    conn = get_db()
    c = conn.cursor()

    # نحذف الدفعة وكل بياناتها التابعة
    c.execute("DELETE FROM feed WHERE batch_id=?", (batch_id,))
    c.execute("DELETE FROM medications WHERE batch_id=?", (batch_id,))
    c.execute("DELETE FROM extra_expenses WHERE batch_id=?", (batch_id,))
    c.execute("DELETE FROM mortality WHERE batch_id=?", (batch_id,))
    c.execute("DELETE FROM sales WHERE batch_id=?", (batch_id,))
    c.execute("DELETE FROM batches WHERE id=?", (batch_id,))

    conn.commit()
    conn.close()

    flash("🗑️ تم حذف الدفعة وكل بياناتها", "warning")
    return redirect(url_for("index"))


# =========================
# ❌ حذف أي عنصر فرعي
# =========================
@app.route("/feed/delete/<int:id>/<int:batch_id>")
def delete_feed(id, batch_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM feed WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash("تم حذف العلف", "warning")
    return redirect(url_for("view_batch", batch_id=batch_id))


@app.route("/med/delete/<int:id>/<int:batch_id>")
def delete_med(id, batch_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM medications WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash("تم حذف الدواء", "warning")
    return redirect(url_for("view_batch", batch_id=batch_id))


@app.route("/extra/delete/<int:id>/<int:batch_id>")
def delete_extra(id, batch_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM extra_expenses WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash("تم حذف المصروف", "warning")
    return redirect(url_for("view_batch", batch_id=batch_id))


# =========================
# ➕ إضافة/حذف النافق
# =========================
@app.route("/mortality/add/<int:batch_id>", methods=["GET", "POST"])
def add_mortality(batch_id):
    if request.method == "POST":
        date = request.form["date"]
        count = int(request.form["count"]) if request.form.get("count") else 0
        note = request.form.get("note", "")

        conn = get_db()
        c = conn.cursor()
        c.execute(
            "INSERT INTO mortality (batch_id, date, count, note) VALUES (?, ?, ?, ?)",
            (batch_id, date, count, note),
        )
        conn.commit()
        conn.close()
        flash("✅ تم تسجيل النافق", "success")
        return redirect(url_for("view_batch", batch_id=batch_id))

    return render_template("add_mortality.html", batch_id=batch_id)


@app.route("/mortality/edit/<int:id>/<int:batch_id>", methods=["GET", "POST"])
def edit_mortality(id, batch_id):
    conn = get_db()
    c = conn.cursor()
    if request.method == "POST":
        date = request.form["date"]
        count = int(request.form.get("count", 0) or 0)
        note = request.form.get("note", "")
        c.execute("UPDATE mortality SET date=?, count=?, note=? WHERE id=?", (date, count, note, id))
        conn.commit()
        conn.close()
        flash("✅ تم تحديث سجل النافق", "success")
        return redirect(url_for("view_batch", batch_id=batch_id))
    c.execute("SELECT * FROM mortality WHERE id=?", (id,))
    rec = c.fetchone()
    conn.close()
    return render_template("edit_mortality.html", record=rec, batch_id=batch_id)

@app.route("/mortality/delete/<int:id>/<int:batch_id>")
def delete_mortality(id, batch_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM mortality WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash("تم حذف سجل النافق", "warning")
    return redirect(url_for("view_batch", batch_id=batch_id))


# =========================
# ➕ إضافة/حذف بيع فعلي
# =========================
@app.route("/sales/add/<int:batch_id>", methods=["GET", "POST"])
def add_sale(batch_id):
    if request.method == "POST":
        date = request.form["date"]
        quantity = int(request.form.get("quantity", 0) or 0)
        average_weight_kg = float(request.form.get("average_weight_kg", 0) or 0)
        price_per_kg = float(request.form.get("price_per_kg", 0) or 0)
        note = request.form.get("note", "")

        total_weight_kg = quantity * average_weight_kg
        total_price = total_weight_kg * price_per_kg

        conn = get_db()
        c = conn.cursor()
        c.execute(
            """
            INSERT INTO sales (batch_id, date, quantity, average_weight_kg, price_per_kg, total_weight_kg, total_price, note)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (batch_id, date, quantity, average_weight_kg, price_per_kg, total_weight_kg, total_price, note),
        )
        conn.commit()
        conn.close()
        flash("✅ تم تسجيل عملية البيع", "success")
        return redirect(url_for("view_batch", batch_id=batch_id))

    return render_template("add_sale.html", batch_id=batch_id)


@app.route("/sales/edit/<int:id>/<int:batch_id>", methods=["GET", "POST"])
def edit_sale(id, batch_id):
    conn = get_db()
    c = conn.cursor()
    if request.method == "POST":
        date = request.form["date"]
        quantity = int(request.form.get("quantity", 0) or 0)
        average_weight_kg = float(request.form.get("average_weight_kg", 0) or 0)
        price_per_kg = float(request.form.get("price_per_kg", 0) or 0)
        total_weight_kg = quantity * average_weight_kg
        total_price = total_weight_kg * price_per_kg
        note = request.form.get("note", "")
        c.execute(
            "UPDATE sales SET date=?, quantity=?, average_weight_kg=?, price_per_kg=?, total_weight_kg=?, total_price=?, note=? WHERE id=?",
            (date, quantity, average_weight_kg, price_per_kg, total_weight_kg, total_price, note, id),
        )
        conn.commit()
        conn.close()
        flash("✅ تم تحديث عملية البيع", "success")
        return redirect(url_for("view_batch", batch_id=batch_id))
    c.execute("SELECT * FROM sales WHERE id=?", (id,))
    rec = c.fetchone()
    conn.close()
    return render_template("edit_sale.html", record=rec, batch_id=batch_id)


# =========================
# ✏️ تعديل الدفعة
# =========================
@app.route("/batch/edit/<int:batch_id>", methods=["GET", "POST"])
def edit_batch(batch_id):
    conn = get_db()
    c = conn.cursor()
    if request.method == "POST":
        name = request.form["name"]
        breed = request.form["breed"]
        start_date = request.form["start_date"]
        initial_count = int(request.form.get("initial_count", 0) or 0)
        chick_price = float(request.form.get("chick_price", 0) or 0)
        c.execute(
            "UPDATE batches SET name=?, breed=?, start_date=?, initial_count=?, chick_price=? WHERE id=?",
            (name, breed, start_date, initial_count, chick_price, batch_id),
        )
        conn.commit()
        conn.close()
        flash("✅ تم تحديث بيانات الدفعة", "success")
        return redirect(url_for("view_batch", batch_id=batch_id))
    c.execute("SELECT * FROM batches WHERE id=?", (batch_id,))
    batch = c.fetchone()
    conn.close()
    return render_template("edit_batch.html", batch=batch)

@app.route("/sales/delete/<int:id>/<int:batch_id>")
def delete_sale(id, batch_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM sales WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash("تم حذف عملية البيع", "warning")
    return redirect(url_for("view_batch", batch_id=batch_id))

# =========================
# 📊 التقارير
# =========================
@app.route("/report/<int:batch_id>", methods=["GET", "POST"])
def report(batch_id):
    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT * FROM batches WHERE id=?", (batch_id,))
    batch = c.fetchone()

    c.execute("SELECT SUM(price) FROM feed WHERE batch_id=?", (batch_id,))
    feed_total = c.fetchone()[0] or 0

    c.execute("SELECT SUM(price) FROM medications WHERE batch_id=?", (batch_id,))
    meds_total = c.fetchone()[0] or 0

    c.execute("SELECT SUM(price) FROM extra_expenses WHERE batch_id=?", (batch_id,))
    extra_total = c.fetchone()[0] or 0

    chicks_total = batch["chick_price"] * batch["initial_count"]
    total_expenses = feed_total + meds_total + extra_total + chicks_total

    # جمع بيانات النافق والمبيعات
    c.execute("SELECT COALESCE(SUM(count),0) FROM mortality WHERE batch_id=?", (batch_id,))
    total_mortality = c.fetchone()[0] or 0

    c.execute("SELECT COALESCE(SUM(quantity),0), COALESCE(SUM(total_weight_kg),0), COALESCE(SUM(total_price),0) FROM sales WHERE batch_id=?", (batch_id,))
    row = c.fetchone()
    total_sold_qty = row[0] if row else 0
    total_sold_weight = row[1] if row else 0
    sales_total = row[2] if row else 0

    birds_remaining = max(batch["initial_count"] - total_mortality - total_sold_qty, 0)

    # حساب الإيرادات والأرباح بناءً على مدخلات المستخدم للتقدير للمتبقي
    avg_weight = None
    price_per_kg = None
    mortality_count = 0  # للإبقاء على الحقل في النموذج السابق إن أردنا تقديراً مستقلاً
    birds_available = None
    revenue_estimate = None
    profit_estimate = None

    if request.method == "POST":
        try:
            avg_weight = float(request.form.get("average_weight_kg", "0") or 0)
            price_per_kg = float(request.form.get("price_per_kg", "0") or 0)
            mortality_count = int(request.form.get("mortality_count", "0") or 0)
        except ValueError:
            flash("المدخلات غير صحيحة.", "danger")

        if avg_weight is not None and price_per_kg is not None:
            if mortality_count < 0:
                mortality_count = 0
            if mortality_count > batch["initial_count"]:
                mortality_count = batch["initial_count"]

            birds_available = batch["initial_count"] - mortality_count
            revenue_estimate = birds_available * avg_weight * price_per_kg
            profit_estimate = revenue_estimate - total_expenses

    conn.close()
    return render_template(
        "report.html",
        batch=batch,
        feed_total=feed_total,
        meds_total=meds_total,
        extra_total=extra_total,
        chicks_total=chicks_total,
        total_expenses=total_expenses,
        total_mortality=total_mortality,
        total_sold_qty=total_sold_qty,
        total_sold_weight=total_sold_weight,
        sales_total=sales_total,
        birds_remaining=birds_remaining,
        average_weight_kg=avg_weight,
        price_per_kg=price_per_kg,
        mortality_count=mortality_count,
        birds_available=birds_available,
        revenue_estimate=revenue_estimate,
        profit_estimate=profit_estimate,
    )


# =========================
# 🧩 تشغيل التطبيق
# =========================
if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
