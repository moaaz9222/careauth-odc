# CareAuth AI — Test Cases & Sample Files Guide 🧪

تم تجهيز **مجموعة كاملة من ملفات الـ Test Cases الطبية** بصيغة PDF الحقيقية داخل المجلد:
📂 **`test_data/sample_documents/`**

---

## 📁 قائمة الملفات الطبية التجريبية الجاهزة للاستخدام:

| اسم الملف | نوع المستند (Doc Type) | الغرض من الاختبار |
|---|---|---|
| `01_insurance_card_ahmed_ali.pdf` | `insurance_card` | بطاقة التأمين الطبي للمريض |
| `02_physician_order_mri_brain.pdf` | `physician_order` | طلب الطبيب لعمل رنين مغناطيسي للمخ (CPT 70551) |
| `03_clinical_progress_notes.pdf` | `clinical_notes` | ملاحظات العيادة وتاريخ العلاج التحفظي |
| `04_prior_imaging_report_2024.pdf` | `prior_imaging_report` | **المستند الناقص** الذي يحتاجه النظام لفك حظر الإرسال (Act 1) |
| `05_physician_notes_detailed_addendum.pdf` | `physician_notes_detailed` | **تقرير الطبيب المفصل** لفك رفض التأمين في المحاولة الأولى (Act 2) |
| `06_physician_order_ct_abdomen.pdf` | `physician_order` | طلب أشعة مقطعية على البطن (CPT 74177) |
| `07_lab_results_panel.pdf` | `lab_results` | نتائج التحاليل المخبرية للمريض |
| `08_referral_letter_specialist.pdf` | `physician_order` | خطاب تحويل لاستشارة استشاري (CPT 99245) |

---

## 🧪 حالات الاختبار الأربعة (Test Cases):

### 1️⃣ Test Case 1: السيناريو الكامل للموافقة المسبقة (Happy Path + Rejection Resolution)
* **المريض:** `Ahmed Ali` | **الخطة:** `ABC Gold PPO` | **الخدمة:** `MRI Brain without contrast (70551)`
* **الملفات المبدئية:** `01_insurance_card_ahmed_ali.pdf`, `02_physician_order_mri_brain.pdf`, `03_clinical_progress_notes.pdf`
* **النتيجة المتوقعة:**
  1. التحليل يكتشف نقص `Previous Imaging Report` ويحظر الإرسال (`NEEDS_DOCUMENTS`).
  2. عند رفع `04_prior_imaging_report_2024.pdf` وإعادة التحليل، تتحول الحالة إلى `READY_FOR_SUBMISSION`.
  3. عند إرسال المحاولة الأولى (Attempt 1)، يرد التأمين بالرفض لنقص التفاصيل السريرية (`ACTION_REQUIRED`).
  4. يقدم المساعد خطة علاجية ويرفع المستخدم `05_physician_notes_detailed_addendum.pdf`.
  5. عند إعادة الإرسال (Attempt 2)، يرد التأمين بالموافقة النهائية (`APPROVED`) ورقم الموافقة `ABC-AUTH-88214`.

---

### 2️⃣ Test Case 2: خدمة مغطاة بدون موافقة مسبقة (Covered Service)
* **المريض:** `Sarah Chen` | **الخطة:** `ABC Gold PPO` | **الخدمة:** `Specialist Consultation (99245)`
* **الملفات:** `01_insurance_card_ahmed_ali.pdf`, `08_referral_letter_specialist.pdf`
* **النتيجة المتوقعة:** النظام يؤكد أن الخدمة مغطاة تلقائياً ولا تتطلب موافقة مسبقة (`status: covered`).

---

### 3️⃣ Test Case 3: خدمة مستبعدة من الوثيقة (Policy Exclusion)
* **المريض:** `James Wilson` | **الخطة:** `ABC Gold PPO` | **الخدمة:** `Knee Arthroscopy (29881)`
* **النتيجة المتوقعة:** يوضح الذكاء الاصطناعي أن الإجراء مستبعد من جدول المنافع (`status: not_covered`).

---

### 4️⃣ Test Case 4: حواجز الأمان والتحقق السلبي (Security & Negative Tests)
* **محاولة رفع ملف `.exe`:** يتم رفضه فوراً بكود `415 UNSUPPORTED_FILE_TYPE`.
* **محاولة رفع ملف أكبر من 10 ميجابايت:** يتم رفضه بكود `413 FILE_TOO_LARGE`.
* **محاولة كتابة سياق سريري قصير (< 20 حرف):** يتم رفضه بكود `422 VALIDATION_ERROR`.
* **محاولة الإرسال أثناء وجود مستندات ناقصة:** يتم منعه بكود `409 SUBMISSION_BLOCKED`.

---

## ⚡ تشغيل الاختبارات الآلية بضغطة زر:
```bash
python run_test_cases.py
```
