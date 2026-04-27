# IKK HR Bot 🤖

بوت تيليجرام لخدمات الموارد البشرية — IKK Group

---

## هيكل المشروع

```
ikk_bot/
├── bot.py              ← البوت الرئيسي
├── employees.py        ← تحميل وبحث الموظفين
├── pdf_filler.py       ← ملء فورمات PDF تلقائياً
├── email_sender.py     ← إرسال إيميل HR
├── tracker.py          ← تتبع الطلبات
├── requirements.txt    ← المكتبات المطلوبة
├── .env.example        ← نموذج الإعدادات
├── forms/
│   ├── Leave_form_fillable.pdf
│   └── Declaration_Form_.pdf
├── data/
│   ├── EMP_List.xlsx   ← قاعدة بيانات الموظفين
│   └── requests.json   ← سجل الطلبات (يتولد تلقائياً)
└── signatures/         ← توقيعات مؤقتة
```

---

## خطوات التشغيل

### 1. إنشاء البوت على تيليجرام
- تواصل مع @BotFather على تيليجرام
- اكتب `/newbot` واتبع الخطوات
- احتفظ بالـ **Token**

### 2. تثبيت المكتبات
```bash
pip install -r requirements.txt
```

### 3. إعداد الإعدادات
```bash
cp .env.example .env
# عدّل .env وأضف:
# - TELEGRAM_BOT_TOKEN
# - SMTP_USER (إيميل Gmail)
# - SMTP_PASSWORD (App Password من Google)
# - HR_EMAIL
```

**للحصول على Gmail App Password:**
1. اذهب لـ myaccount.google.com
2. Security → 2-Step Verification (فعّلها)
3. App Passwords → اختر "Mail" → احفظ الـ Password

### 4. تشغيل البوت
```bash
python bot.py
```

### 5. تحديث بيانات الموظفين
استبدل ملف `data/EMP_List.xlsx` بالنسخة الجديدة وأعد تشغيل البوت.

---

## الخدمات المتاحة

| الخدمة | الوصف | متاحة لـ |
|--------|-------|---------|
| طلب إجازة | سنوية / مرضية / بدون راتب + PDF موقّع | Labor فقط |
| تتبع طلب | متابعة حالة الطلب برقمه | الكل |

---

## تدفق طلب الإجازة

```
الموظف يبدأ
    ↓ اختيار اللغة (عربي / English / اردو)
    ↓ إدخال الرقم الوظيفي أو رقم الإقامة
    ↓ التحقق من الـ Excel (Labor فقط)
    ↓ اختيار نوع الإجازة
    ↓ تاريخ الذهاب والعودة
    ↓ الوجهة (داخل / خارج المملكة)
    ↓ [لو خارج] مدينة المغادرة والبلد المقصود
    ↓ ملخص للتأكيد
    ↓ رسم التوقيع بالإصبع
    ↓ PDF يتملى تلقائياً
    ↓ [لو خارج المملكة] فورم الإقرار كمان
    ↓ إيميل لـ HR مع الفورمات المرفقة
    ↓ ✅ "تم تقديم طلبك — رقم #LV-XXXXXXXX"
```

---

## إضافة خدمة جديدة لاحقاً

1. أضف الـ PDF الخاص بها في `forms/`
2. أضف دالة `fill_xxx_form()` في `pdf_filler.py`
3. أضف حالات المحادثة في `bot.py`
4. أضف الترجمات الثلاثة في قاموس `TEXTS`

---

## الاستضافة (مجانية)

**Railway.app:**
```bash
# ارفع المشروع على GitHub (بدون .env)
# اربط Railway بـ GitHub
# أضف Environment Variables من .env
# Deploy!
```
