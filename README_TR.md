# Instagram DM Aracı - Toplu Mesaj Geri Çekme & Sohbet Yedekleme

**English** | [Türkçe](README_TR.md)

[instagrapi](https://github.com/subzeroid/instagrapi) kullanan, aşağıdakileri yapabilen bir Python aracı:
- Oturum kalıcılığıyla Instagram'a giriş (Kullanıcı Adı/Şifre, 2FA ve Tarayıcı Oturum ID desteği)
- **Hesap Geneli Temizlik:** **Gelen kutunuzdaki TÜM sohbetleri** tarar ve dolandırıcılık linklerini, fotoğrafları ve mesajları tek tıkla toplu olarak geri çeker
- Etkileşimli Sonraki Sayfa sayfalamasıyla tüm gelen kutusu geçmişinize göz atın ve kaydırın
- Doğru imleç tabanlı sayfalama ile herhangi bir sohbette sınırsız mesaj görüntüleme
- Mesajları **Tüm Mesajlar**, **Anahtar Kelimeler**, **Fotoğraf & Medya**, **Link & URL** veya **Yakın Tarih Aralığı** ile arama ve filtreleme
- Kendi mesajlarınızı, dolandırıcılık linklerini, fotoğrafları, videoları ve kaybolan (tek seferlik) snap'leri **toplu geri çekme**
- **Sohbet İndirme & Yedekleme:** Sohbetleri okunabilir **Metin (.txt)**, yapılandırılmış **JSON (.json)** ve etkileşimli **HTML (.html)** olarak dışa aktarma; isteğe bağlı medya indirme (fotoğraf, video, sesli not)

> **Not:** Aracın ekrandaki menüleri İngilizce görüntülenir; bu rehber tüm seçenekleri Türkçe açıklar.

---

## ⚠️ Yasal Uyarı
Bu araç Instagram'ın özel (private) API'leriyle etkileşir ve Instagram'ın Hizmet Şartlarını ihlal edebilir.
**Kullanım riski size aittir.** Hesabınız geçici veya kalıcı kısıtlamalara maruz kalabilir.

---

## 📚 Yeni Başlayanlar İçin Eksiksiz Rehber

Bu rehber, daha önce hiç kod yazmamış olsanız bile bilmeniz gereken her şeyi adım adım anlatır!

### Adım 1: Python'ı Kurun

Python, bu aracın yazıldığı programlama dilidir. Önce onu kurmanız gerekir.

#### Windows için:
1. [python.org/downloads](https://www.python.org/downloads/) adresine gidin
2. Sarı renkli "Download Python 3.x.x" düğmesine tıklayın
3. Kurulum dosyasını çalıştırın
4. **ÖNEMLİ:** Alttaki "Add Python to PATH" yazan kutuyu işaretleyin
5. "Install Now" düğmesine tıklayın
6. Kurulumun bitmesini bekleyin

#### Mac için:
1. Terminal'i açın (Cmd+Space'e basın, "Terminal" yazın, Enter'a basın)
2. Homebrew yüklü değilse yükleyin:
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```
3. Python'ı kurun:
   ```bash
   brew install python3
   ```

#### Linux (Ubuntu/Debian) için:
1. Terminal'i açın
2. Şu komutları çalıştırın:
   ```bash
   sudo apt update
   sudo apt install python3 python3-pip
   ```

**Python'ın kurulu olduğunu doğrulayın:**
Terminal'i (Windows'ta Komut İstemi) açın ve şunu yazın:
```bash
python3 --version
```
`Python 3.x.x` benzeri bir çıktı görmelisiniz.

---

### Adım 2: Aracı İndirin

İki seçeneğiniz var:

#### Seçenek A: ZIP olarak indirin (Yeni başlayanlar için daha kolay)
1. Bu GitHub sayfasının en üstündeki yeşil "Code" düğmesine tıklayın
2. "Download ZIP" seçeneğine tıklayın
3. ZIP dosyasını kolay bulabileceğiniz bir klasöre çıkartın (Masaüstü veya Belgeler gibi)
4. Nereye kaydettiğinizi hatırlayın!

#### Seçenek B: Git kullanarak
1. Terminal/Komut İstemi'ni açın
2. Aracı kaydetmek istediğiniz yere gidin:
   ```bash
   cd Desktop
   ```
3. Depoyu klonlayın:
   ```bash
   git clone https://github.com/startingfrom0rating/Instagram-Message-Deleter.git
   cd Instagram-Message-Deleter
   ```

---

### Adım 3: Gerekli Kütüphaneleri Kurun

Bu aracın Instagram'a bağlanmak için `instagrapi`'ye ihtiyacı var. "App out of date" hatalarını önlemek için en son sürümü kurduğunuzdan emin olun:

1. Terminal/Komut İstemi'ni açın
2. Aracı kaydettiğiniz klasöre gidin:
   ```bash
   cd path/to/Instagram-Message-Deleter
   ```
   Windows örneği: `cd C:\Kullanıcınız\Desktop\Instagram-Message-Deleter`
   Mac/Linux örneği: `cd ~/Desktop/Instagram-Message-Deleter`

3. Gerekli kütüphaneleri kurun:
   ```bash
   pip install --upgrade -r requirements.txt
   ```
   veya:
   ```bash
   pip install --upgrade instagrapi
   ```

---

### Adım 4: Aracı Çalıştırın

1. Aracın klasöründe olduğunuzdan emin olun (Adım 3'ten)
2. Aracı çalıştırın:
   ```bash
   python instagram_dm_tool.py
   ```
   (Mac/Linux'ta `python3 instagram_dm_tool.py`)

3. Ana menüyü göreceksiniz:
   ```
   =======================================================
      INSTAGRAM DM TOOL - UNLIMITED PAGINATION & UNSEND
   =======================================================
   Status:   NOT LOGGED IN (Select Option 1 to connect)
   Thread:   None selected (Select Option 2 or 3)

   Options:
   1. Login / Account (Username/Password or Session ID Cookie)
   2. List Conversations (Browse Inbox with Next-Page pagination)
   3. Select Conversation (by Username or Thread ID)
   4. View Messages (Unlimited pagination in selected conversation)
   5. Search / Filter Messages (In selected conversation)
   6. Unsend Queued Messages (In selected conversation)
   7. CLEAN ALL CONVERSATIONS (Account-Wide Scam Unsend)
   8. DOWNLOAD / EXPORT CHAT (Save to TXT, JSON, HTML & Media) [NEW]
   9. Logout / Switch Account
   10. Exit
   ```

---

### Adım 5: Instagram'a Giriş Yapın

Menüden **Seçenek 1**'i seçin. İki giriş yöntemi arasından seçim yapabilirsiniz:

#### Yöntem 1: Kullanıcı Adı & Şifre (2FA destekli)
- Instagram kullanıcı adınız ve şifrenizle standart giriş.
- Hesabınızda **İki Adımlı Doğrulama (2FA)** açıksa, araç sizden 6 haneli SMS veya Authenticator kodu girmenizi ister. *(2FA'yı kapatmanıza GEREK YOK!)*

#### Yöntem 2: Tarayıcı Oturum ID Çerezi (ÖNERİLEN)
> [!TIP]
> **"Instagram uygulaması güncel değil" hatası alırsanız, checkpoint doğrulaması istenirse veya hesabınız yakın zamanda hack'lendiyse/işaretlendiyse bu yöntemi kullanın!**
> Bu yöntem, aktif tarayıcı oturumunuzu kullanarak mobil uygulama giriş kısıtlamalarını tamamen atlar.

**`sessionid` değerinizi nasıl alırsınız:**
1. Web tarayıcınızda (Chrome, Edge, Firefox, Brave, Safari) https://www.instagram.com adresini açın ve giriş yaptığınızdan emin olun.
2. Geliştirici Araçlarını açın:
   - **Chrome / Edge / Brave**: `F12` tuşuna basın (veya herhangi bir yere sağ tıklayın -> **Inspect**) -> **Application** sekmesine tıklayın -> soldaki **Cookies** bölümünü genişletin -> `https://www.instagram.com` adresine tıklayın.
   - **Firefox**: `F12` tuşuna basın -> **Storage** -> **Cookies** -> `https://www.instagram.com`.
   - **Safari**: Tercihler -> Gelişmiş -> "Develop menüsünü göster" seçeneğini işaretleyin, sonra sağ tıklayın -> Inspect Element -> Storage -> Cookies.
3. **`sessionid`** adlı çerezi bulun.
4. **Değerine** çift tıklayın ve tüm diziyi kopyalayın.
5. Araçta **Seçenek 1 -> Yöntem 2**'yi seçin, `sessionid` değerinizi yapıştırın ve Enter'a basın.

Oturumunuz otomatik olarak `session.json` dosyasına kaydedilir, böylece çalıştırmalar arasında giriş yapmış kalırsınız! Dosya **sadece sahip erişimine izin veren izinlerle (`0600`)** yazılır ve `.gitignore` sayesinde git'e girmez — bu dosyaya şifreniz gibi davranın.

---

### Adım 6: Hesap Geneli Dolandırıcılık Temizliği (Seçenek 7 - HACK'LENEN HESAPLAR İÇİN ÖNERİLEN)

> [!IMPORTANT]
> Hesabınız hack'lendiyse ve dolandırıcı **birçok kişiye veya gelen kutunuzdaki herkese** mesaj attıysa **Seçenek 7**'yi kullanın!
> Sohbetleri tek tek seçmenize veya kaydırmanıza **gerek yoktur**!

1. **Seçenek 7: CLEAN ALL CONVERSATIONS (Account-Wide Scam Unsend)** seçeneğini seçin.
2. **Kaç sohbet taranacağını seçin:**
   - 1. Son 25 sohbet
   - 2. Son 50 sohbet
   - 3. Son 100 sohbet
   - 4. **Gelen kutusundaki TÜM sohbetler (Tam gelen kutusu taraması)**
   - 5. Özel sayı (örn. `150`)
3. **Neyi geri çekeceğinizi seçin:**
   - **1. Sizin gönderdiğiniz TÜM mesajlar ve medyalar:** Hesabınızın gönderdiği her şeyi geri çeker.
   - **2. Sadece Linkler ve URL'ler:** Tüm dolandırıcılık sitelerini ve linkleri geri çeker.
   - **3. Sadece Fotoğraflar ve Videolar:** Tüm dolandırıcılık fotoğraflarını, kaybolan snap'leri ve medyaları geri çeker.
   - **4. Anahtar Kelimeler:** `oyla,link,hediye,kripto` gibi kelimeler içeren mesajları geri çeker.
4. **Tarih Aralığı seçin (Eski mesajlarınızı korur):**
   - Hack döneminde gönderilen mesajları silmek için son 3 veya 7 günü kapsaması adına `3` veya `7` girin.
   - Ya da tüm zamanları taramak için Enter'a basın.
5. Tüm sohbetlerde bulunan mesajların özetini inceleyin.
6. Onaylamak için `YES` yazın. Araç, bunların hepsini her sohbette otomatik olarak geri çekecek!

---

### Adım 7: Tek Bir Sohbeti Temizleme (Seçenekler 2, 5, 6)

Sadece belirli bir sohbeti temizlemeniz gerekiyorsa:

#### Adım 7.1: Sohbeti Seçin
- **Seçenek 2 (Gelen Kutusuna Göz At):** Sohbetleri 20'şerli listeler. Gelen kutunuzda aşağı kaydırmak için `N` yazın veya sohbeti seçmek için numarasını girin.
- **Seçenek 3 (Kullanıcı Adıyla Seç):** Instagram kullanıcı adını doğrudan girin.

#### Adım 7.2: Mesajları Filtreleyin
1. `5` yazıp Enter'a basın (**Search / Filter Messages**).
2. Şunlardan birini seçin:
   - `1` sizin gönderdiğiniz tüm mesajlar için.
   - `2` anahtar kelimeler için.
   - `3` fotoğraflar ve videolar için.
   - `4` linkler ve URL'ler için.
3. Sohbet geçmişinde kaç mesajın taranacağını girin (örn. `1000`, `5000` veya daha fazla). Araç, daha eski mesaj geçmişine erişmek için doğru imleç sayfalaması kullanır.

#### Adım 7.3: Geri Çekin
1. `6` yazıp Enter'a basın (**Unsend Queued Messages**).
2. Onaylamak için `YES` yazın.

---

### Adım 8: Sohbet İndirme & Dışa Aktarma (Seçenek 8 - YENİ)

Instagram direkt mesaj geçmişinizi istediğiniz zaman yedekleyebilir ve indirebilirsiniz!

1. **Seçenek 8: DOWNLOAD / EXPORT CHAT (Save to TXT, JSON, HTML & Media)** seçeneğini seçin.
2. Ne indirmek istediğinizi seçin:
   - **1. Şu an seçili olan sohbeti indir:** Etkin olan sohbeti dışa aktarır.
   - **2. Kullanıcı adı veya Thread ID ile sohbet indir:** Herhangi bir kullanıcıyı veya sohbet ID'sini arayın.
   - **3. Toplu İndirme: Birden fazla / tüm gelen kutusu sohbetleri:** Tüm gelen kutunuzu tek seferde yedekleyin!
     - Kaç sohbet indirileceğini seçin: son `10`, `25`, `50` sohbet, **TÜMÜ** veya özel bir sayı.
     - Mesaj derinliği sohbet başına uygulanır (varsayılan `2000`, sınırsız için `0`).
3. **Mesaj derinliğini seçin:**
   - Tek sohbet: varsayılan `5000` mesaj (sınırsız geçmiş için `0`). Derin imleç sayfalaması en eski mesaja kadar geriye gider.
4. **Dışa aktarma biçimini seçin:**
   - `1. Tüm biçimler (TXT + JSON + HTML) [Önerilen]`
   - `2. Düz Metin (.txt)` — Temiz kronolojik transkript.
   - `3. JSON (.json)` — Üst veri ve zaman damgalarıyla tam yapılandırılmış arşiv.
   - `4. HTML Sohbet Görünümü (.html)` — Etkileşimli aramalı, Instagram temalı şık karanlık mod arayüzü!
5. **Medya dosyalarını indirin:**
   - Tüm fotoğraf, video ve sesli notları yerel `media/` klasörüne indirmek için `y` yazın.
   - Sadece metin kaydedip medya linklerini tutmak için `n` yazın.

Tüm dışa aktarmalar `exports/` klasörü içinde düzenli şekilde saklanır:
```
exports/
├── @friend_123456789/          <-- Tek sohbet dışa aktarımı
│   ├── chat.html        <-- Instagram'daki gibi okumak için tarayıcıda açın!
│   ├── chat.txt         <-- Düz metin biçimi
│   ├── chat.json        <-- Tam yapılandırılmış veri
│   └── media/           <-- Fotoğraflar, videolar, ses kayıtları
└── inbox_backup_20260101_120000/   <-- Toplu gelen kutusu yedeği (sohbet başına bir klasör)
    └── @friend_123456789/ ...
```

---

## 🎯 Yaygın Kullanım Senaryoları

### Geri Çekme / Hesap Sıfırlamadan Önce Sohbetleri Yedekleme
1. Giriş yapın (Seçenek 1).
2. **Seçenek 8 (DOWNLOAD / EXPORT CHAT)** seçin.
3. Seçenek 1 (Seçili sohbet) veya Seçenek 3 (Toplu gelen kutusu yedeği) seçin.
4. Biçim `1` (Tüm biçimler) ve medya için `y` seçin.
5. Tüm sohbet geçmişiniz ve medyanız bilgisayarınıza güvenle kaydedildi!

### Hack'lenmiş Hesaptan Kurtarma (Hesap Geneli Temizlik)
1. Tarayıcınızın **Oturum ID'si** ile giriş yapın (Seçenek 1 -> Yöntem 2).
2. **Seçenek 7 (CLEAN ALL CONVERSATIONS)** seçin.
3. `4` (Gelen kutusundaki TÜM sohbetler) veya `3` (100 sohbet) seçin.
4. `1` (Sizin gönderdiğiniz TÜM mesajlar), `2` (Linkler ve URL'ler) veya `3` (Fotoğraflar ve Videolar) seçin.
5. (İsteğe bağlı) Eski kişisel sohbetleri korumak için son 3 gün için `3` girin.
6. `YES` ile onaylayın ve aracın tüm dolandırıcılık içeriğini tüm sohbetlerden otomatik olarak geri çekmesine izin verin!

---

## ❓ SSS & Sorun Giderme

### Sorun: "Your version of Instagram is out of date. Please upgrade your app to log in to Instagram." (`needs_upgrade`)
**Çözüm:**
**Oturum ID Çerezi ile Giriş** kullanın (Seçenek 1 -> Yöntem 2). Tarayıcı çerezleri, mobil uygulama istemci sürümü kullanımdan kaldırmalarını ve checkpoint doğrulamalarını tamamen atlar.

### Sorun: "Sadece en üstteki geçmişi tarıyor, gönderdiğim tüm mesajları taramıyor"
**Çözüm:**
Son güncelleme şunları içerir:
1. **Seçenek 7 (Hesap Geneli Temizlik):** Gelen kutunuzun tamamında sayfalama yapar ve tüm sohbetleri otomatik olarak temizler.
2. **Gelen Kutusu Sayfalaması (Seçenek 2):** Gelen kutunuzdaki eski sohbetlere inmek için `N` yazın.
3. **Derin Sohbet Sayfalaması (Seçenek 4 ve 5):** Doğru imleç sayfalama parametreleri düzeltildi (`seq_id="40065"`, `limit="20"`, `oldest_cursor` ve `MINCURSOR` algılama), böylece bir sohbetin derinliklerinde arama yapmak binlerce eski mesajı yükleyebilir.

### Sorun: İki Adımlı Doğrulama (2FA) açık
**Çözüm:**
2FA'yı kapatmanıza **gerek yok**! Araç 6 haneli doğrulama kodunuzu ister; ya da 2FA'yı tamamen atlamak için Oturum ID ile (Yöntem 2) giriş yapabilirsiniz.

### S: Karşı tarafın mesajlarını da siler mi?
**C:** Hayır. Instagram yalnızca kendi hesabınızın gönderdiği mesajların geri çekilmesine izin verir. Araç, diğer sohbet katılımcılarının gönderdiği mesajları otomatik olarak korur ve yok sayar.

### S: Fotoğraflar, videolar ve kaybolan snap'ler geri çekilebilir mi?
**C:** Evet! Araç; metin mesajlarını, doğrudan fotoğraf/video yüklemelerini, kaybolan snap'leri (`raven_media`), reels'leri ve paylaşılan linkleri geri çekmeyi destekler.

### S: Geri çekme ne kadar hızlı?
**C:** Araç, Instagram hız limitlerine uymak ve geçici hesap kilitlenmelerini önlemek için silmeler arasında kısa bir süre bekler (akışa göre 0,4–1,5 saniye; hesap geneli temizlik sırasında sohbetler arasında ~1 saniye).

---

## 📋 Gereksinimler
- Python 3.8+
- `instagrapi>=3.2.0` (`pip install --upgrade -r requirements.txt` ile kurun)

---

## 🧪 Testleri Çalıştırma
Proje, `unittest` ve mock'larla oluşturulmuş bir birim test paketi içerir (mesaj ayrıştırma, sayfalama, dışa aktarma biçimleri ve indirme akışları) — Instagram hesabı gerekmez:

```bash
python -m unittest test_instagram_dm_tool -v
```

---

## 📄 Lisans
Bu proje MIT Lisansı ile lisanslanmıştır - ayrıntılar için [LICENSE](LICENSE) dosyasına bakın.
