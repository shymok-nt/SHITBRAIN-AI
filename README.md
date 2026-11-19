# SHITBRAIN AI — Yerel Absürt Mizah Stüdyosu

Türkçe internet mizahını örneklerden analiz etmek için ücretsiz, yerel bir ilk prototip. **Python dışında zorunlu Python paketi yoktur.**

## Windows'ta çalıştır

1. Depoyu ZIP olarak indirip klasöre çıkar veya `git clone https://github.com/shymok-nt/SHITBRAIN-AI.git` ile klonla.
2. `baslat.bat` dosyasına çift tıkla; tarayıcıda **http://127.0.0.1:8765** açılır. Alternatif: `python app.py`.
3. Görsel, tweet ekran görüntüsü veya video sürükle-bırak ile yükle. Dosyalar `data/uploads/`, kayıtlar `data/shitbrain.sqlite3` altında yerelde kalır.
4. AI analizi ve üretimi için [Ollama](https://ollama.com/download) kur. Terminalde `ollama pull gemma3:4b` çalıştır. Ollama arka planda açık olmalı. Ardından arşivden **Analiz et**, sonra **5 paylaşım üret**.

> `gemma3:4b` birçok bilgisayarda çalışır ama RAM ve indirme alanı gerektirir. Daha güçlü bir bilgisayarda farklı görsel/metin modeli seçmek için `SHITBRAIN_VISION_MODEL` ve `SHITBRAIN_TEXT_MODEL` ortam değişkenlerini kullanabilirsin.

## Bu sürümde neler var?

- Görsel/video/tweet ekran görüntüsü yükleme (dosya başına en fazla 25 MB)
- SQLite arşivi, yerel medya gösterimi ve isteğe bağlı açıklama
- Ollama görsel analizi: metin okuma ve absürt mizah yapısı üzerine yorum
- Video için **yalnızca bir örnek kare** analizi (bilgisayarda FFmpeg varsa); ses, hareket ve tüm video analizi henüz yok
- Kayıtlı referansların analizleriyle **5 özgün kısa paylaşım önerisi** üretme
- API anahtarı veya ücretli bulut hesabı gerektirmeme

## Önemli ayrım

Bu MVP **model ağırlıklarını eğitmez**. Yüklenen örnekleri kaydedip bunların analizini yeni içerik üretirken bağlam olarak kullanır (reference-guided generation). Gerçek LoRA fine-tuning, otomatik tweet metni ayıklama, çok kareli video analizi, görsel ve video **üretimi** ileriki sürümlerin konusudur.

## Teknik

- Python standart kütüphanesi ile HTTP sunucu
- SQLite veri tabanı
- Saf HTML/CSS/JS, ayrı frontend build zorunluluğu yok
- Ollama `/api/generate` üzerinden yerel çok modlu model
- FFmpeg isteğe bağlı video kare çıkarma

**Güvenlik:** Varsayılan olarak yalnızca `127.0.0.1` dinlenir. Portu internete açma. Başkalarının içeriklerini izinsiz yeniden yayımlama.

## Sonraki geliştirmeler

1. Ekran görüntülerindeki tweet metinlerini OCR ile ayrı alana çıkarma.
2. Videodan çoklu kare + ses transkripti + mizah ritmi analizi.
3. Etiketleme ekranı (komedi türü, absürtlük seviyesi, Türkçe doğallık).
4. İzinli verilerle QLoRA eğitimi için ücretsiz GPU not defteri.
5. Yerel görsel/video üreticileriyle (isteğe bağlı, donanıma göre) entegrasyon.
