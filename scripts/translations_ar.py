"""Fill `unicap/locale/ar/LC_MESSAGES/django.po` from the table below, then compile it.

    uv run manage.py makemessages -l ar --ignore=node_modules --ignore=.venv --ignore=static
    uv run python scripts/translations_ar.py
    uv run manage.py compilemessages -l ar

Entries already translated in the .po file are kept; new msgids missing here are listed.
"""

from pathlib import Path

import polib

PO_FILE = (
    Path(__file__).resolve().parent.parent
    / "unicap"
    / "locale"
    / "ar"
    / "LC_MESSAGES"
    / "django.po"
)

AR: dict[str, str] = {
    # navigation and layout
    "overview": "نظرة عامة",
    "data": "البيانات",
    "settings": "الإعدادات",
    "dashboard": "لوحة المعلومات",
    "board": "اللوحة",
    "capacity report": "تقرير الطاقة الاستيعابية",
    "welcome": "أهلاً بك",
    "main navigation": "التنقل الرئيسي",
    "close menu": "إغلاق القائمة",
    "collapse sidebar": "طي الشريط الجانبي",
    "collapse": "طي",
    "toggle sidebar": "إظهار / إخفاء الشريط الجانبي",
    "theme": "المظهر",
    "light": "فاتح",
    "dark": "داكن",
    "system": "حسب النظام",
    "user menu": "قائمة المستخدم",
    "administration": "الإدارة",
    "log out": "تسجيل الخروج",
    "log in": "تسجيل الدخول",
    "username": "اسم المستخدم",
    "password": "كلمة المرور",
    "the username or password is not right.": "اسم المستخدم أو كلمة المرور غير صحيحة.",
    "university capacity calculator": "حاسبة الطاقة الاستيعابية للجامعة",
    "English": "الإنجليزية",
    "Arabic": "العربية",
    "no chapter yet": "لا يوجد فصل بعد",
    "unpin": "إلغاء التثبيت",
    "pin beside the table": "تثبيت بجانب الجدول",
    "Welcome to UniCap": "أهلاً بك في UniCap",
    "UniCap calculates how many students the university may take from its teaching staff. "
    "Everything lives in a chapter (a term, or a scenario): its specializations, faculties, "
    "employees and contracts.": "يحسب UniCap عدد الطلاب الذين يحق للجامعة قبولهم بحسب كادرها "
    "التدريسي. كل شيء يعيش داخل فصل (فصل دراسي، أو سيناريو): اختصاصاته وكلياته ومدرّسوه وعقوده.",
    "create the first chapter": "إنشاء الفصل الأول",
    "or load the sample data": "أو حمّل البيانات التجريبية",
    # apps
    "core": "الأساس",
    "chapters": "الفصول",
    "education": "التعليم",
    "human resources": "الموارد البشرية",
    # models and fields
    "chapter": "الفصل",
    "name": "الاسم",
    "notes": "ملاحظات",
    "max students": "الحد الأعلى للطلاب",
    "calculate masters": "احتساب حملة الماجستير",
    "created at": "تاريخ الإنشاء",
    "is default": "افتراضي",
    "is active": "مفعّل",
    "faculty": "الكلية",
    "faculties": "الكليات",
    "specialization": "الاختصاص",
    "specializations": "الاختصاصات",
    "accepted specialization": "اختصاص مقبول",
    "accepted specializations": "الاختصاصات المقبولة",
    "employee": "المدرّس",
    "employees": "المدرّسون",
    "contract": "العقد",
    "contracts": "العقود",
    "students per PhD": "طلاب لكل دكتور",
    "min staff percentage": "الحد الأدنى لنسبة الملاك",
    "current students": "الطلاب الحاليون",
    "target students": "الطلاب المستهدفون",
    "min specialized PhDs": "الحد الأدنى لدكاترة الاختصاص",
    "max specialized PhDs": "الحد الأعلى لدكاترة الاختصاص",
    "min supported PhDs": "الحد الأدنى للدكاترة الداعمين",
    "max supported PhDs": "الحد الأعلى للدكاترة الداعمين",
    "type": "النوع",
    "percentage": "النسبة",
    "min percentage": "أدنى نسبة",
    "max percentage": "أعلى نسبة",
    "min teachers": "أدنى عدد مدرّسين",
    "max teachers": "أعلى عدد مدرّسين",
    "position": "الترتيب",
    "signing order": "ترتيب التوقيع",
    "degree": "الشهادة",
    "contract type": "نوع العقد",
    "employment type": "نوع التعيين",
    # domain values
    "specialized": "اختصاصي",
    "supported": "داعم",
    "PhD": "دكتوراه",
    "master": "ماجستير",
    "masters": "حملة الماجستير",
    "fulltime": "متفرغ",
    "parttime": "جزئي",
    "staff": "ملاك",
    "borrowed": "معار",
    "MA": "ماجستير",
    "PT": "جزئي",
    "FT staff": "متفرغ ملاك",
    "FT borrowed": "متفرغ معار",
    "counted": "محتسب",
    "not counted": "غير محتسب",
    "unsigned": "غير موقّع",
    "not calculated": "خارج الحساب",
    "specialization not accepted here": "الاختصاص غير مقبول هنا",
    "parttime beyond fulltime of its type": "جزئي يتجاوز المتفرغين من نوعه",
    "masters beyond specialized fulltime": "ماجستير يتجاوز متفرغي الاختصاص",
    "specialization above its max share": "الاختصاص فوق حصته العليا",
    "specialization above its max teachers": "الاختصاص فوق حده الأعلى من المدرّسين",
    "above the faculty's max of its type": "فوق الحد الأعلى للكلية من نوعه",
    "inactive: not calculated": "معطّل: خارج الحساب",
    "masters not calculated in this chapter": "الماجستير لا يُحتسب في هذا الفصل",
    "staff ratio too low": "نسبة الملاك منخفضة",
    "specialization share too low": "حصة الاختصاص منخفضة",
    "current students over capacity": "الطلاب الحاليون فوق الطاقة",
    "too few teachers": "عدد المدرّسين قليل",
    "too few of a type": "عدد نوع ما قليل",
    # strategies
    "strategy": "الاستراتيجية",
    "maximize students": "أكبر عدد من الطلاب",
    "maximize teacher usage": "أقصى استفادة من المدرّسين",
    "minimize overflowing": "أقل فائض",
    "meet student targets": "بلوغ أهداف الطلاب",
    "fewest changes": "أقل تغييرات",
    "fewest teachers": "أقل عدد من المدرّسين",
    "less salaries": "أقل رواتب",
    "best staff percentage": "أفضل نسبة ملاك",
    "The most students the ministry allows.": "أكبر عدد من الطلاب تسمح به الوزارة.",
    "As many counted teachers as possible, as few wasted.": "أكبر عدد ممكن من المدرّسين المحتسبين وأقل هدر.",
    "The lowest share of signed contracts that are not counted.": "أقل نسبة من العقود الموقّعة غير المحتسبة.",
    "Reach every faculty's target students first, then maximize.": "بلوغ هدف كل كلية أولاً، ثم زيادة الطلاب.",
    "Become compliant re-signing as few contracts as possible.": "تحقيق الامتثال بإعادة توقيع أقل عدد من العقود.",
    "The most students with the fewest teachers: frees the rest.": "أكبر عدد من الطلاب بأقل عدد من المدرّسين: يحرّر الباقين.",
    "The most students with the cheapest team: masters and parttime before fulltime, borrowed "
    "before staff, supported before specialized.": "أكبر عدد من الطلاب بأقل كلفة: الماجستير وغير "
    "المتفرغين قبل المتفرغين، والمعار قبل الملاك، والداعم قبل الاختصاصي.",
    "The highest staff share in the weakest faculty, then overall; may give up students.": "أعلى "
    "نسبة ملاك في أضعف كلية ثم عموماً؛ قد يتنازل عن بعض الطلاب.",
    # dashboard, board, report
    "this chapter's data breaks a rule": "بيانات هذا الفصل تخالف قاعدة",
    "open the board": "فتح اللوحة",
    "capacity": "الطاقة الاستيعابية",
    "students the university may take": "الطلاب الذين يحق للجامعة قبولهم",
    "chapter max": "حد الفصل",
    "counted teachers": "المدرّسون المحتسبون",
    "%(n)s not counted": "%(n)s غير محتسب",
    "%(n)s unsigned": "%(n)s غير موقّع",
    "%(n)s overflowing": "%(n)s فائض",
    "missing to targets": "النقص عن الأهداف",
    "missing to target": "النقص عن الهدف",
    "teaching capacity": "الطاقة التدريسية",
    "teaching capacity above the max students": "طاقة تدريسية فوق الحد الأعلى للطلاب",
    "compliance": "الامتثال",
    "compliant": "ممتثل",
    "not compliant": "غير ممتثل",
    "compliant: no violation.": "ممتثل: لا توجد مخالفات.",
    "every faculty is compliant.": "كل الكليات ممتثلة.",
    "violations": "المخالفات",
    "drag to reorder": "اسحب لإعادة الترتيب",
    "drag to reorder lanes": "اسحب لإعادة ترتيب الأعمدة",
    "capacity by faculty": "الطاقة حسب الكلية",
    "staff share of PhDs": "نسبة الملاك من الدكاترة",
    "max": "الأعلى",
    "min": "الأدنى",
    "target": "الهدف",
    "now": "الحالي",
    "after": "بعد",
    "minimum": "الحد الأدنى",
    "no faculty yet.": "لا توجد كليات بعد.",
    "all contracts": "كل العقود",
    "find a teacher": "ابحث عن مدرّس",
    "preview the moves before applying them": "معاينة التنقلات قبل تطبيقها",
    "optimize": "تحسين",
    "reset": "إعادة ضبط",
    "reset the board": "إعادة ضبط اللوحة",
    "copy this chapter with all of its data to try another scenario": "انسخ هذا الفصل بكل بياناته "
    "لتجربة سيناريو آخر",
    "duplicate chapter": "نسخ الفصل",
    "drag a card to another lane · click: details · double-click: on / off": "اسحب بطاقة إلى عمود "
    "آخر · نقرة: التفاصيل · نقرتان: تفعيل / تعطيل",
    "students": "طلاب",
    "signed contracts": "العقود الموقّعة",
    "overflowing": "الفائض",
    "staff (weakest faculty)": "الملاك (أضعف كلية)",
    "yes,no": "نعم,لا",
    "yes": "نعم",
    "no": "لا",
    "the current placement is already the best this strategy finds.": "التوزيع الحالي هو الأفضل "
    "الذي تجده هذه الاستراتيجية.",
    "a heuristic search (two starts and local moves), not a proven optimum. Employment terms "
    "never change, only faculties.": "بحث تقريبي (بدايتان وتنقلات محلية) وليس حلاً أمثل مثبتاً. "
    "شروط التعيين لا تتغير، الكليات فقط.",
    "apply these moves": "تطبيق هذه التنقلات",
    "print": "طباعة",
    "specialized FT staff": "اختصاصي متفرغ ملاك",
    "specialized FT borrowed": "اختصاصي متفرغ معار",
    "specialized PT": "اختصاصي جزئي",
    "supported FT staff": "داعم متفرغ ملاك",
    "supported FT borrowed": "داعم متفرغ معار",
    "supported PT": "داعم جزئي",
    "PhD equivalents": "مكافئ الدكاترة",
    "per PhD": "لكل دكتور",
    "chapter capacity": "طاقة الفصل",
    "capped at": "بحد أعلى",
    "each cell: counted / signed. Contracts left out of the calculation are not in either.": "كل "
    "خلية: المحتسب / الموقّع. العقود خارج الحساب ليست في أي منهما.",
    "make all %(signed)s signed contract(s) of %(name)s unsigned? Their terms stay; only the "
    "faculties are cleared.": "جعل كل العقود الموقّعة (%(signed)s) في %(name)s غير موقّعة؟ "
    "تبقى شروطها؛ تُفرّغ الكليات فقط.",
    "faculties allow": "ما تسمح به الكليات",
    "unused": "غير مستخدم",
    "no faculty in this chapter yet: add one to sign contracts to it.": "لا توجد كلية في هذا الفصل "
    "بعد: أضف كلية لتوقيع العقود عليها.",
    "issues": "المشكلات",
    "%(name)s on %(place)s: %(status)s · capacity would be %(capacity)s": "%(name)s في "
    "%(place)s: %(status)s · ستصبح الطاقة %(capacity)s",
    "%(count)s contract(s) are unsigned now.": "أصبحت %(count)s عقود غير موقّعة.",
    "%(count)s contract(s) re-signed.": "أعيد توقيع %(count)s عقود.",
    # chapters
    "e.g. 2026 / Fall": "مثال: 2026 / الخريف",
    "name of the copy": "اسم النسخة",
    "a chapter with this name already exists.": "يوجد فصل بهذا الاسم.",
    "caps the chapter's capacity; empty: no cap": "يحدّ طاقة الفصل؛ فارغ: بلا حد",
    "off: masters are left out of this chapter's calculation": "معطّل: لا يُحتسب حملة الماجستير "
    "في هذا الفصل",
    "the copy holds every specialization, faculty (with its numbers and shares), employee and "
    "contract of this chapter, notes included. Try another scenario in it without touching this "
    "one.": "تحتوي النسخة كل اختصاص وكلية (بأرقامها وحصصها) ومدرّس وعقد في هذا الفصل، مع "
    "الملاحظات. جرّب فيها سيناريو آخر دون المساس بهذا الفصل.",
    "duplicate": "نسخ",
    "default": "افتراضي",
    "shown": "معروض",
    "calculated": "محتسب",
    "left out": "مستبعد",
    "show": "عرض",
    "make default": "جعله افتراضياً",
    "chapter actions": "إجراءات الفصل",
    "%(name)s is the default chapter now.": "أصبح %(name)s الفصل الافتراضي.",
    "%(name)s (copy)": "%(name)s (نسخة)",
    "%(name)s created: it is the chapter shown now.": "أُنشئ %(name)s: وهو الفصل المعروض الآن.",
    "duplicate %(name)s": "نسخ %(name)s",
    "Create a chapter first: every page shows one chapter.": "أنشئ فصلاً أولاً: كل صفحة تعرض "
    "فصلاً واحداً.",
    # tables, filters, forms
    "search": "بحث",
    "from": "من",
    "to": "إلى",
    "any": "الكل",
    "still in use by %(names)s: remove it from them first.": "ما زال مستخدماً من قبل %(names)s: "
    "أزله منها أولاً.",
    "delete": "حذف",
    "select rows first.": "اختر صفوفاً أولاً.",
    "close": "إغلاق",
    "edit": "تعديل",
    "save, then start a new one": "احفظ ثم ابدأ سجلاً جديداً",
    "save & new": "حفظ وجديد",
    "save": "حفظ",
    "cancel": "إلغاء",
    "an Excel (xlsx) or CSV file with the same columns as an export. Rows refer to each other by "
    "name; a row whose name exists is updated, new ones are added, nothing is deleted. All rows "
    "are saved, or none.": "ملف Excel (xlsx) أو CSV بأعمدة التصدير نفسها. تشير الصفوف إلى بعضها "
    "بالاسم؛ يُحدَّث الصف الموجود اسمه، ويضاف الجديد، ولا يحذف شيء. تُحفظ كل الصفوف أو لا شيء.",
    "columns": "الأعمدة",
    "import": "استيراد",
    "apply": "تطبيق",
    "clear every filter": "مسح كل عوامل التصفية",
    "words, or a query like": "كلمات، أو استعلام مثل",
    "filters": "التصفية",
    "drag to reorder, check to show": "اسحب لإعادة الترتيب، وحدّد للإظهار",
    "reset columns": "إعادة ضبط الأعمدة",
    "export / import": "تصدير / استيراد",
    "files": "الملفات",
    "export to Excel": "تصدير إلى Excel",
    "export to CSV": "تصدير إلى CSV",
    "import a file": "استيراد ملف",
    "new": "جديد",
    "select all": "تحديد الكل",
    "click: sort by this column · shift+click: add it as another level": "نقرة: الترتيب حسب هذا "
    "العمود · Shift+نقرة: إضافته كمستوى آخر",
    "select": "تحديد",
    "details": "التفاصيل",
    "nothing matches the search and filters.": "لا شيء يطابق البحث والتصفية.",
    "clear filters": "مسح التصفية",
    "nothing here yet.": "لا شيء هنا بعد.",
    "%(shown)s of %(total)s %(what)s": "%(shown)s من %(total)s %(what)s",
    "rows per page": "صفوف في الصفحة",
    "pages": "الصفحات",
    "first page": "الصفحة الأولى",
    "previous page": "الصفحة السابقة",
    "next page": "الصفحة التالية",
    "last page": "الصفحة الأخيرة",
    "%(name)s created.": "أُنشئ %(name)s.",
    "%(name)s saved.": "حُفظ %(name)s.",
    "%(name)s is on.": "فُعّل %(name)s.",
    "%(name)s is off.": "عُطّل %(name)s.",
    "new %(what)s": "%(what)s جديد",
    "%(count)s deleted.": "حُذف %(count)s.",
    "on": "مفعّل",
    "off": "معطّل",
    "Choose a file.": "اختر ملفاً.",
    "%(count)s row(s) imported.": "استُورد %(count)s صف.",
    "import %(what)s": "استيراد %(what)s",
    "Only .xlsx and .csv files can be imported, not %(name)s.": "يمكن استيراد ملفات ‎.xlsx "
    "و‎.csv فقط، وليس %(name)s.",
    "%(name)s cannot be read: %(error)s": "تعذّرت قراءة %(name)s: %(error)s",
    "accepts": "يقبل",
    "active": "مفعّل",
    "inactive": "معطّل",
    "used": "مستخدم",
    "used by a faculty or employee": "مستخدم من كلية أو مدرّس",
    "e.g. Dentistry": "مثال: طب الأسنان",
    "e.g. Computer Science": "مثال: علوم الحاسوب",
    "e.g. Dr. Sami": "مثال: د. سامي",
    "this chapter already has a faculty with this name.": "في هذا الفصل كلية بهذا الاسم.",
    "this chapter already has a specialization with this name.": "في هذا الفصل اختصاص بهذا الاسم.",
    "each specialization is accepted once: %(names)s": "يُقبل كل اختصاص مرة واحدة: %(names)s",
    # faculty details and form
    "free seats": "المقاعد الشاغرة",
    "this chapter's numbers": "أرقام هذا الفصل",
    "specialized PhDs": "دكاترة الاختصاص",
    "supported PhDs": "الدكاترة الداعمون",
    "head counts": "الأعداد",
    "signed": "موقّع",
    "specialized fulltime staff": "اختصاصي متفرغ ملاك",
    "specialized fulltime borrowed": "اختصاصي متفرغ معار",
    "specialized parttime": "اختصاصي جزئي",
    "supported fulltime staff": "داعم متفرغ ملاك",
    "supported fulltime borrowed": "داعم متفرغ معار",
    "supported parttime": "داعم جزئي",
    "share": "الحصة",
    "min – max": "الأدنى – الأعلى",
    "teachers": "المدرّسون",
    "it accepts no specialization yet: no contract can be counted here.": "لا تقبل أي اختصاص بعد: "
    "لا يمكن احتساب أي عقد هنا.",
    "contracts signed here": "العقود الموقّعة هنا",
    "no contract is signed here.": "لا يوجد عقد موقّع هنا.",
    "leave the share empty for the new method (only specialized / supported matters). Min / max "
    "default to the share itself. Drag rows to reorder.": "اترك الحصة فارغة للطريقة الجديدة "
    "(يهم الاختصاصي / الداعم فقط). الأدنى / الأعلى يساويان الحصة افتراضياً. اسحب الصفوف لإعادة "
    "ترتيبها.",
    "share %%": "الحصة %%",
    "min %%": "الأدنى %%",
    "max %%": "الأعلى %%",
    "accept a specialization": "قبول اختصاص",
    "remove": "إزالة",
    "inactive: its contracts are not calculated": "معطّل: عقوده خارج الحساب",
    "accepted by": "تقبله",
    "no faculty accepts it.": "لا تقبله أي كلية.",
    "no employee holds it.": "لا يحمله أي مدرّس.",
    "now · target · max": "الحالي · الهدف · الأعلى",
    # employees and contracts
    "signed to a faculty": "موقّع على كلية",
    "has a contract": "لديه عقد",
    "no contract": "بلا عقد",
    "empty: unsigned (placed on the board later)": "فارغ: غير موقّع (يوضع على اللوحة لاحقاً)",
    "employee off": "المدرّس معطّل",
    "switched off": "معطّل",
    "when a group overflows, the contracts signed last are the ones not counted.": "عندما تفيض "
    "مجموعة، فالعقود الموقّعة أخيراً هي التي لا تُحتسب.",
    "contract in this chapter": "العقد في هذا الفصل",
    "the contract is switched off: it is not calculated.": "العقد معطّل: خارج الحساب.",
    "edit the contract": "تعديل العقد",
    "no contract yet.": "لا يوجد عقد بعد.",
    "order": "الترتيب",
    "terms": "الشروط",
    "status": "الحالة",
    # Word reports and their templates
    "UniCap": "UniCap",
    "Word": "Word",
    "print staff": "طباعة الكادر",
    "faculty staff": "كادر الكلية",
    "report": "التقرير",
    "report template": "قالب تقرير",
    "report templates": "قوالب التقارير",
    "language": "اللغة",
    "file": "الملف",
    "updated at": "تاريخ التعديل",
    "built-in templates": "القوالب المضمّنة",
    "variables": "المتغيرات",
    "a Word (.docx) file holding docxtpl tags such as {{ chapter.name }}": (
        "ملف Word (.docx) يحوي وسوم docxtpl مثل {{ chapter.name }}"
    ),
    "The Word template cannot be used: %(error)s": "تعذّر استخدام قالب Word: %(error)s",
    # violations (the domain's rules, as sentences)
    "%(faculty)s: staff are %(percentage)s%% of PhDs, minimum is %(minimum)s%%": (
        "%(faculty)s: نسبة الملاك %(percentage)s%% من حملة الدكتوراه، والحد الأدنى %(minimum)s%%"
    ),
    "%(faculty)s: %(specialization)s is %(share)s%% of counted PhDs, minimum is %(minimum)s%%": (
        "%(faculty)s: نسبة %(specialization)s %(share)s%% من حملة الدكتوراه المحتسبين، "
        "والحد الأدنى %(minimum)s%%"
    ),
    "%(faculty)s: %(current_students)s current students, but the capacity is %(capacity)s": (
        "%(faculty)s: عدد الطلاب الحاليين %(current_students)s، لكن الطاقة الاستيعابية %(capacity)s"
    ),
    "%(faculty)s: %(specialization)s has %(counted)s counted PhD(s), minimum is %(minimum)s": (
        "%(faculty)s: لدى %(specialization)s %(counted)s من حملة الدكتوراه المحتسبين، "
        "والحد الأدنى %(minimum)s"
    ),
    "%(faculty)s: %(counted)s counted %(type)s PhD(s), minimum is %(minimum)s": (
        "%(faculty)s: %(counted)s من حملة الدكتوراه المحتسبين من النوع %(type)s، "
        "والحد الأدنى %(minimum)s"
    ),
    # domain errors (the domain's rules, as sentences)
    ", ": "، ",
    "%(faculty)s: duplicated specializations %(names)s": "%(faculty)s: اختصاصات مكررة %(names)s",
    "%(faculty)s does not accept %(names)s": "%(faculty)s لا تقبل %(names)s",
    "%(specialization)s: min teachers (%(minimum)s) cannot exceed max teachers (%(maximum)s)": "%(specialization)s: لا يمكن أن يتجاوز الحد الأدنى للمدرسين (%(minimum)s) الحد الأعلى (%(maximum)s)",
    "%(specialization)s: the min share (%(minimum)s%%) must be between 0 and the max share (%(maximum)s%%), at most 100%%": "%(specialization)s: يجب أن تكون النسبة الدنيا (%(minimum)s%%) بين 0 والنسبة العليا (%(maximum)s%%)، وألا تتجاوز 100%%",
    "%(specialization)s: share %(percentage)s%% is not between %(minimum)s%% and %(maximum)s%%": "%(specialization)s: النسبة %(percentage)s%% ليست بين %(minimum)s%% و%(maximum)s%%",
    "%(faculty)s: students per PhD must be positive": "%(faculty)s: يجب أن يكون عدد الطلاب لكل دكتوراه أكبر من صفر",
    "%(faculty)s: min %(type)s PhDs (%(minimum)s) cannot exceed max %(type)s PhDs (%(maximum)s)": "%(faculty)s: لا يمكن أن يتجاوز الحد الأدنى لحملة الدكتوراه من النوع %(type)s (%(minimum)s) الحد الأعلى (%(maximum)s)",
    "%(faculty)s: target students (%(target)s) cannot exceed max students (%(maximum)s)": "%(faculty)s: لا يمكن أن يتجاوز عدد الطلاب المستهدف (%(target)s) الحد الأعلى للطلاب (%(maximum)s)",
    "%(faculty)s: duplicated shares %(names)s": "%(faculty)s: نسب مكررة %(names)s",
    "%(faculty)s: specialization percentages sum to %(total)s%%, more than 100%%": "%(faculty)s: مجموع نسب الاختصاصات %(total)s%%، أي أكثر من 100%%",
    "%(employee)s: a parttime contract is always borrowed": "%(employee)s: العقد الجزئي يكون دائماً معاراً",
    "%(chapter)s: max students (%(max_students)s) cannot exceed the faculties' limit (%(limit)s)": "%(chapter)s: لا يمكن أن يتجاوز الحد الأعلى للطلاب (%(max_students)s) مجموع حدود الكليات (%(limit)s)",
    "%(chapter)s: specializations listed more than once: %(names)s": "%(chapter)s: اختصاصات مذكورة أكثر من مرة: %(names)s",
    "%(chapter)s: employees listed more than once: %(names)s": "%(chapter)s: موظفون مذكورون أكثر من مرة: %(names)s",
    "%(chapter)s: faculties listed more than once: %(names)s": "%(chapter)s: كليات مذكورة أكثر من مرة: %(names)s",
    "%(chapter)s: employees with more than one contract: %(names)s": "%(chapter)s: موظفون لديهم أكثر من عقد: %(names)s",
    "%(chapter)s: employees of specializations not in this chapter: %(names)s": "%(chapter)s: موظفون من اختصاصات ليست في هذا الفصل: %(names)s",
    "%(chapter)s: faculties accepting specializations not in this chapter: %(names)s": "%(chapter)s: كليات تقبل اختصاصات ليست في هذا الفصل: %(names)s",
    "%(chapter)s: contracts of employees not in this chapter: %(names)s": "%(chapter)s: عقود لموظفين ليسوا في هذا الفصل: %(names)s",
    "%(chapter)s: contracts signed to faculties not in this chapter: %(names)s": "%(chapter)s: عقود موقعة لكليات ليست في هذا الفصل: %(names)s",
    "%(chapter)s: %(faculty)s is not in this chapter": "%(chapter)s: %(faculty)s ليست في هذا الفصل",
    "%(chapter)s: %(employee)s has no contract": "%(chapter)s: ليس لدى %(employee)s عقد",
    "%(owner)s: %(fields)s cannot be negative": "%(owner)s: لا يمكن أن تكون القيم سالبة: %(fields)s",
    # settings and the admin panel
    "medium": "متوسط",
    "large": "كبير",
    "extra large": "كبير جداً",
    "full width": "بعرض الشاشة",
    "project name": "اسم المشروع",
    "modal size": "حجم النافذة",
    "resizable modals": "نوافذ قابلة لتغيير الحجم",
    "drag a modal's corner to resize it, or maximize it": "اسحب زاوية النافذة لتغيير حجمها، أو كبّرها",
    "remember table state": "تذكّر حالة الجداول",
    "a table opens again with the filters, search, sorting and page it was left with": "يُفتح الجدول مجدداً بالفلاتر والبحث والترتيب والصفحة التي تُرك عليها",
    "app settings": "إعدادات التطبيق",
    "empty: the app's default": "فارغ: القيمة الافتراضية للتطبيق",
    "form modal size": "حجم نافذة النموذج",
    "details modal size": "حجم نافذة التفاصيل",
    "chapters settings": "إعدادات الفصول",
    "specializations settings": "إعدادات الاختصاصات",
    "faculties settings": "إعدادات الكليات",
    "employees settings": "إعدادات الموظفين",
    "contracts settings": "إعدادات العقود",
    "restore": "استعادة الحجم",
    "maximize": "تكبير",
    "admin panel": "لوحة الإدارة",
    # backups and search
    "%(section)s: %(names)s cannot be removed, still used by %(users)s; restore the whole chapter instead.": "%(section)s: لا يمكن حذف %(names)s لأنها مستخدمة في %(users)s؛ استعد الفصل كاملاً بدلاً من ذلك.",
    "%(owner)s: no %(name)s in this chapter; restore it first.": "%(owner)s: لا يوجد %(name)s في هذا الفصل؛ استعده أولاً.",
    "the file is too big (50 MB at most).": "الملف كبير جداً (50 ميغابايت كحد أقصى).",
    "uploaded: %(name)s": "مرفوع: %(name)s",
    "choose the chapter to restore into: the backup's chapter is gone.": "اختر الفصل الذي ستُستعاد إليه النسخة: فصلها الأصلي لم يعد موجوداً.",
    "before restoring: %(backup)s": "قبل الاستعادة: %(backup)s",
    "before restoring the whole system": "قبل استعادة النظام كاملاً",
    "a chapter named %(name)s exists already.": "يوجد فصل باسم %(name)s مسبقاً.",
    "restored as a new chapter": "استُعيدت كفصل جديد",
    "choose a chapter to back up.": "اختر فصلاً لأخذ نسخة احتياطية منه.",
    "unknown section %(section)s: %(sections)s": "قسم غير معروف %(section)s: %(sections)s",
    "this file is not a backup: %(error)s": "هذا الملف ليس نسخة احتياطية: %(error)s",
    "this file is not a backup of this app.": "هذا الملف ليس نسخة احتياطية من هذا التطبيق.",
    "this backup's version is not supported: %(v)s": "إصدار هذه النسخة الاحتياطية غير مدعوم: %(v)s",
    "this backup is incomplete.": "هذه النسخة الاحتياطية غير مكتملة.",
    "whole system": "النظام كاملاً",
    "section": "القسم",
    "backup file": "ملف النسخة الاحتياطية",
    "a .json file downloaded from the backups page": "ملف \u200e.json\u200e نُزّل من صفحة النسخ الاحتياطية",
    "restore into": "الاستعادة إلى",
    "or as a new chapter named": "أو كفصل جديد باسم",
    "choose a chapter, or name a new one.": "اختر فصلاً، أو سمِّ فصلاً جديداً.",
    "scope": "النطاق",
    "size": "الحجم",
    "created by": "أنشأها",
    "backup": "نسخة احتياطية",
    "backups": "النسخ الاحتياطية",
    "Can restore a backup": "يمكنه استعادة نسخة احتياطية",
    "this backup cannot be taken.": "لا يمكن أخذ هذه النسخة الاحتياطية.",
    "backup saved: %(backup)s": "حُفظت النسخة الاحتياطية: %(backup)s",
    "backup uploaded: %(backup)s": "رُفعت النسخة الاحتياطية: %(backup)s",
    "restored. What it replaced is saved as: %(backup)s": "تمت الاستعادة. ما استُبدل محفوظ في: %(backup)s",
    "backup deleted.": "حُذفت النسخة الاحتياطية.",
    "delete the backup %(backup)s? It cannot be undone.": "حذف النسخة الاحتياطية %(backup)s؟ لا يمكن التراجع عن ذلك.",
    "back up the whole system": "نسخ النظام كاملاً احتياطياً",
    "back up %(name)s": "نسخ %(name)s احتياطياً",
    "upload a backup": "رفع نسخة احتياطية",
    "all": "الكل",
    "download": "تنزيل",
    "no backup yet.": "لا توجد نسخ احتياطية بعد.",
    "restore a backup": "استعادة نسخة احتياطية",
    "every chapter and the settings are replaced by this backup.": "ستُستبدل كل الفصول والإعدادات بهذه النسخة الاحتياطية.",
    "the chapter's rows and settings are replaced by this backup, or it becomes a new chapter.": "ستُستبدل بيانات الفصل وإعداداته بهذه النسخة الاحتياطية، أو تصبح فصلاً جديداً.",
    "the chapter's %(section)s are replaced by this backup; its other rows stay.": "ستُستبدل %(section)s في الفصل بهذه النسخة الاحتياطية؛ وتبقى بقية بياناته.",
    "what is replaced is saved as a backup first, so this can be undone.": "يُحفظ ما سيُستبدل كنسخة احتياطية أولاً، فيمكن التراجع عن ذلك.",
    "uploading only saves it here: restore it from the list afterwards.": "الرفع يحفظ النسخة هنا فقط: استعدها من القائمة بعد ذلك.",
    "upload": "رفع",
    "back up the %(what)s": "نسخ %(what)s احتياطياً",
    "back up this chapter": "نسخ هذا الفصل احتياطياً",
    "restore from a backup": "الاستعادة من نسخة احتياطية",
    "type to search": "اكتب للبحث",
    "no match": "لا نتائج",
    # bulk actions, the rows' menu and the search
    "a parttime contract is always borrowed.": "العقد الجزئي يكون دائماً معاراً.",
    "students per PhD must be positive.": "يجب أن يكون عدد الطلاب لكل دكتوراه أكبر من صفر.",
    "leave masters out": "استبعاد حملة الماجستير",
    "clear max students": "مسح الحد الأعلى للطلاب",
    "activate": "تفعيل",
    "deactivate": "إيقاف",
    "unsign": "إلغاء التوقيع",
    "check the fields to change.": "حدّد الحقول التي تريد تغييرها.",
    "%(count)s row(s) changed.": "تغيّر %(count)s صف.",
    "clear accepted specializations": "مسح الاختصاصات المقبولة",
    "clear current students": "مسح عدد الطلاب الحاليين",
    "clear target students": "مسح عدد الطلاب المستهدف",
    "edit the selected rows": "تعديل الصفوف المحددة",
    "change this field": "تغيير هذا الحقل",
    "change %(name)s": "تغيير %(name)s",
    "selected": "محدد",
    "edit fields": "تعديل الحقول",
    "actions": "الإجراءات",
    "see all": "عرض الكل",
    "search everything": "البحث في كل شيء",
    # rounding
    "down (floor)": "للأسفل (floor)",
    "up (ceiling)": "للأعلى (ceiling)",
    "mathematical (half up)": "رياضي (النصف للأعلى)",
    "half down": "النصف للأسفل",
    "half to even (banker's)": "النصف للزوجي (المصرفي)",
    "max share rounding": "تقريب الحد الأعلى للنسبة",
    "a specialization's max percentage in whole teachers: the most it may count": (
        "النسبة القصوى للاختصاص بعدد كامل من المدرّسين: أكثر ما يمكن احتسابه"
    ),
    "min share rounding": "تقريب الحد الأدنى للنسبة",
    "a specialization's min percentage in whole teachers: the fewest it needs": (
        "النسبة الدنيا للاختصاص بعدد كامل من المدرّسين: أقل ما يحتاجه"
    ),
    "min staff rounding": "تقريب الحد الأدنى للملاك",
    "the min staff percentage in whole fulltime staff: the fewest it needs": (
        "النسبة الدنيا للملاك بعدد كامل من المتفرغين الملاك: أقل ما يحتاجه"
    ),
    # masters
    "specialized masters only": "الماجستير المختصون فقط",
    "on: a master is counted only in a faculty where their specialization is specialized": (
        "عند التفعيل: لا يُحتسب حامل الماجستير إلا في كلية يكون اختصاصه فيها اختصاصياً"
    ),
    "masters per PhD": "عدد حملة الماجستير لكل دكتور",
    "how many masters are worth one PhD in capacity": (
        "كم حاملاً للماجستير يعادل دكتوراً واحداً في الطاقة الاستيعابية"
    ),
    "masters rounding": "تقريب الماجستير",
    "how a faculty's masters round to whole PhDs (e.g. one master alone)": (
        "كيف يُقرَّب حملة الماجستير في الكلية إلى عدد كامل من الدكاترة (مثل حامل ماجستير واحد)"
    ),
    "masters per PhD must be positive": "عدد حملة الماجستير لكل دكتور يجب أن يكون موجباً",
    "masters per PhD must be positive.": "عدد حملة الماجستير لكل دكتور يجب أن يكون موجباً.",
    "only specialized masters are calculated": "لا يُحتسب إلا حملة الماجستير المختصون",
    "%(n)s per PhD": "%(n)s لكل دكتور",
    "specialized only": "المختصون فقط",
    # violations, in teachers (PhDs and masters)
    "%(faculty)s: %(specialization)s is %(share)s%% of counted teachers, "
    "minimum is %(minimum)s%%": (
        "%(faculty)s: نسبة %(specialization)s %(share)s%% من المدرّسين المحتسبين، "
        "والحد الأدنى %(minimum)s%%"
    ),
    "%(faculty)s: %(specialization)s has %(counted)s counted teacher(s), minimum is %(minimum)s": (
        "%(faculty)s: لدى %(specialization)s %(counted)s مدرّس محتسب، والحد الأدنى %(minimum)s"
    ),
    "still in use by %(users)s: remove it from them first.": (
        "ما زال مستخدماً من قبل %(users)s: أزله منها أولاً."
    ),
    # optimizer
    "optimizer rounds": "جولات المحسّن",
    "how many times the optimizer goes over every contract looking for a better place: "
    "more can find better placements, but takes longer": (
        "عدد المرات التي يمر فيها المحسّن على كل عقد بحثاً عن مكان أفضل: "
        "الأكثر قد يجد توزيعاً أفضل، لكنه يستغرق وقتاً أطول"
    ),
    # recommendations
    "recommend": "اقتراح",
    "recommend contracts": "اقتراح عقود",
    "the contracts to sign to solve every problem": "العقود الواجب توقيعها لحل كل المشكلات",
    "fewest contracts": "أقل عدد من العقود",
    "low salaries": "رواتب منخفضة",
    "fulltime staff first": "المتفرغون الملاك أولاً",
    "borrowed first": "المعارون أولاً",
    "specialized first": "الاختصاصيون أولاً",
    "The fewest new contracts: each one solves as much as possible.": (
        "أقل عدد من العقود الجديدة: كل عقد يحل أكبر قدر ممكن."
    ),
    "The cheapest contracts that help: masters and parttime before fulltime, "
    "borrowed before staff, supported before specialized.": (
        "أرخص العقود المفيدة: الماجستير والجزئيون قبل المتفرغين، "
        "والمعارون قبل الملاك، والداعمون قبل الاختصاصيين."
    ),
    "Fulltime staff PhDs whenever they help: they raise the staff percentage too.": (
        "دكاترة متفرغون ملاك كلما أفادوا: فهم يرفعون نسبة الملاك أيضاً."
    ),
    "Fulltime borrowed PhDs whenever they help: no new permanent staff.": (
        "دكاترة متفرغون معارون كلما أفادوا: دون ملاك دائم جديد."
    ),
    "Teachers of the faculty's own (specialized) specializations whenever they help.": (
        "مدرّسون من اختصاصات الكلية نفسها (الاختصاصية) كلما أفادوا."
    ),
    "fulltime staff PhD": "دكتور متفرغ ملاك",
    "fulltime borrowed PhD": "دكتور متفرغ معار",
    "parttime PhD": "دكتور غير متفرغ",
    "contracts the university may sign": "العقود التي يمكن للجامعة توقيعها",
    "also reach every target": "بلوغ كل الأهداف أيضاً",
    "besides solving the violations, reach every faculty's target students": (
        "إضافة إلى حل المخالفات، بلوغ العدد المستهدف من الطلاب في كل كلية"
    ),
    "optimize the current contracts first": "تحسين العقود الحالية أولاً",
    "re-sign the current contracts first: new ones only fill what is left": (
        "إعادة توزيع العقود الحالية أولاً: العقود الجديدة تسد ما تبقى فقط"
    ),
    "how many contracts, of which kind, specialization and faculty, the university should "
    "sign so that no violation is left. Nothing is saved.": (
        "كم عقداً، ومن أي نوع واختصاص وكلية، يجب أن توقع الجامعة كي لا تبقى أي مخالفة. لا يُحفظ شيء."
    ),
    "nothing to sign: no problem is left.": "لا شيء للتوقيع: لم تبقَ أي مشكلة.",
    "some problems need more than new contracts (max teachers, max shares, max students): "
    "see what is left below.": (
        "بعض المشكلات تحتاج أكثر من عقود جديدة (الحد الأعلى للمدرّسين أو النسب أو الطلاب): "
        "انظر ما تبقى أدناه."
    ),
    "current students without a seat": "الطلاب الحاليون دون مقعد",
    "count": "العدد",
    "total": "المجموع",
    "left after signing": "ما يبقى بعد التوقيع",
    "a greedy search, faculty by faculty: each step signs the contract that helps the most "
    "for the strategy. Masters are suggested by the PhD they are worth together.": (
        "بحث جشع، كلية تلو الأخرى: كل خطوة توقع العقد الأكثر فائدة حسب الاستراتيجية. "
        "ويُقترح حملة الماجستير بعدد ما يعادل دكتوراً واحداً معاً."
    ),
    # tables
    "clear the filters": "مسح عوامل التصفية",
    "clear the filters (search and sorting stay)": "مسح عوامل التصفية (يبقى البحث والترتيب)",
    # masters and contract type per accepted specialization
    "specialized fulltime": "اختصاصي متفرغ",
    "supported fulltime": "داعم متفرغ",
    "masters of this specialization not calculated here": "ماجستير هذا الاختصاص لا يُحتسب هنا",
    "its contract type does not count here": "نوع عقده لا يُحتسب هنا",
    "the faculty's masters in whole PhDs (e.g. one master alone)": (
        "حملة الماجستير في الكلية بعدد كامل من الدكاترة (مثل حامل ماجستير واحد)"
    ),
    "only this contract type counts for the specialization here; empty: any": (
        "لا يُحتسب للاختصاص هنا إلا هذا النوع من العقود؛ فارغ: أي نوع"
    ),
    "off: the specialization's masters are left out of this faculty": (
        "عند الإيقاف: لا يُحتسب ماجستير هذا الاختصاص في هذه الكلية"
    ),
    "how many of its masters are worth one PhD": "كم حاملاً للماجستير منه يعادل دكتوراً واحداً",
    "%(faculty)s is not in this chapter": "%(faculty)s ليست في هذا الفصل",
    "Contract type: only that type counts for the specialization here (empty: any). "
    "Masters: on / off, and how many make one PhD.": (
        "نوع العقد: لا يُحتسب للاختصاص هنا إلا هذا النوع (فارغ: أي نوع). "
        "الماجستير: تفعيل / إيقاف، وكم حاملاً منهم يعادل دكتوراً واحداً."
    ),
    "calculate masters · masters per PhD": "احتساب الماجستير · عدد حملة الماجستير لكل دكتور",
    # dashboard
    "how each faculty is filled": "كيف امتلأت كل كلية",
    "counted PhDs · inner ring: staff / borrowed": "الدكاترة المحتسبون · الحلقة الداخلية: ملاك / معارون",
    "no counted teacher yet.": "لا يوجد مدرّس محتسب بعد.",
    # API
    "each specialization is listed once: %(names)s": "كل اختصاص يُذكر مرة واحدة: %(names)s",
    "each faculty is listed once: %(names)s": "كل كلية تُذكر مرة واحدة: %(names)s",
}

# Arabic has six plural forms: zero, one, two, few (3-10), many (11-99), other
AR_PLURALS: dict[str, tuple[str, str, str, str, str, str]] = {
    "sign %(counter)s contract": (
        "لا عقود للتوقيع",
        "توقيع عقد واحد",
        "توقيع عقدين",
        "توقيع %(counter)s عقود",
        "توقيع %(counter)s عقداً",
        "توقيع %(counter)s عقد",
    ),
    "%(counter)s move": (
        "لا تنقلات",
        "تنقل واحد",
        "تنقلان",
        "%(counter)s تنقلات",
        "%(counter)s تنقلاً",
        "%(counter)s تنقل",
    ),
    "delete this row? It cannot be undone.": (
        "حذف هذه الصفوف؟ لا يمكن التراجع.",
        "حذف هذا الصف؟ لا يمكن التراجع.",
        "حذف هذين الصفين؟ لا يمكن التراجع.",
        "حذف هذه الصفوف الـ%(counter)s؟ لا يمكن التراجع.",
        "حذف هذه الصفوف الـ%(counter)s؟ لا يمكن التراجع.",
        "حذف هذه الصفوف الـ%(counter)s؟ لا يمكن التراجع.",
    ),
    "%(counter)s violation": (
        "لا مخالفات",
        "مخالفة واحدة",
        "مخالفتان",
        "%(counter)s مخالفات",
        "%(counter)s مخالفة",
        "%(counter)s مخالفة",
    ),
    "accepted by %(counter)s faculty": (
        "لا تقبله أي كلية",
        "تقبله كلية واحدة",
        "تقبله كليتان",
        "تقبله %(counter)s كليات",
        "تقبله %(counter)s كلية",
        "تقبله %(counter)s كلية",
    ),
    "%(counter)s employee": (
        "لا مدرّسين",
        "مدرّس واحد",
        "مدرّسان",
        "%(counter)s مدرّسين",
        "%(counter)s مدرّساً",
        "%(counter)s مدرّس",
    ),
    "apply to this row?": (
        "لا يوجد صفوف.",
        "تطبيق على هذا الصف؟",
        "تطبيق على هذين الصفين؟",
        "تطبيق على هذه الصفوف الـ %(counter)s؟",
        "تطبيق على هذه الصفوف الـ %(counter)s؟",
        "تطبيق على هذه الصفوف الـ %(counter)s؟",
    ),
    "the checked fields change on the selected row.": (
        "لا يوجد صف محدد.",
        "تتغير الحقول المحددة في الصف المحدد.",
        "تتغير الحقول المحددة في الصفين المحددين.",
        "تتغير الحقول المحددة في الصفوف الـ %(counter)s المحددة.",
        "تتغير الحقول المحددة في الصفوف الـ %(counter)s المحددة.",
        "تتغير الحقول المحددة في الصفوف الـ %(counter)s المحددة.",
    ),
}


def main() -> None:
    """Fill the Arabic catalog and list what is missing."""
    catalog = polib.pofile(str(PO_FILE))

    catalog.metadata["Plural-Forms"] = (
        "nplurals=6; plural=n==0 ? 0 : n==1 ? 1 : n==2 ? 2 : "
        "n%100>=3 && n%100<=10 ? 3 : n%100>=11 && n%100<=99 ? 4 : 5;"
    )
    catalog.metadata["Language"] = "ar"
    catalog.metadata["Project-Id-Version"] = "unicap 0.1.0"
    catalog.metadata["Language-Team"] = "Arabic"
    catalog.metadata["Last-Translator"] = "UniCap"

    missing = []

    for entry in catalog:
        if entry.msgid_plural:
            forms = AR_PLURALS.get(entry.msgid)
            if forms:
                entry.msgstr_plural = dict(enumerate(forms))
            elif not any(entry.msgstr_plural.values()):
                missing.append(entry.msgid)
        elif entry.msgid in AR:
            entry.msgstr = AR[entry.msgid]
        elif not entry.msgstr:
            missing.append(entry.msgid)

        if "fuzzy" in entry.flags:
            entry.flags.remove("fuzzy")

    catalog.save()

    print(f"{len(catalog)} entries, {len(missing)} missing")
    for msgid in missing:
        print("  missing:", msgid)


if __name__ == "__main__":
    main()
