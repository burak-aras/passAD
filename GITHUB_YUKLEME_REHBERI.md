# 🚀 Projeyi GitHub'a Yükleme Rehberi

Bilgisayarınızda `git` komutu bulunamadı. Bu projeyi GitHub'a yüklemek için aşağıdaki adımları takip edebilirsiniz.

## Adım 1: Git Kurulumu
Eğer bilgisayarınızda Git yüklü değilse:
1. [Git for Windows](https://git-scm.com/download/win) adresinden Git'i indirin ve kurun.
2. Kurulum bittikten sonra bu projeyi kapatıp tekrar açmanız gerekebilir.

## Adım 2: GitHub Deposu (Repository) Oluşturma
1. [GitHub.com](https://github.com) adresine gidin ve giriş yapın.
2. Sağ üst köşedeki **+** ikonuna tıklayıp **New repository** seçeneğini seçin.
3. **Repository name** kısmına bir isim verin (örn: `passcore-reset-system`).
4. **Public** (herkese açık) veya **Private** (gizli) seçeneğini seçin.
5. "Add a README file", ".gitignore", "license" seçeneklerini **İŞARETLEMEYİN** (zaten hazırladık).
6. **Create repository** butonuna tıklayın.

## Adım 3: Projeyi Yükleme (Komut Satırı ile)
Bu klasörde (`passcore`) sağ tıklayıp "Git Bash Here" diyebilir veya terminali açıp şu komutları sırasıyla yazabilirsiniz:

```bash
# 1. Git'i başlatın
git init

# 2. Tüm dosyaları ekleyin (hazırladığımız .gitignore gereksiz dosyaları engelleyecek)
git add .

# 3. İlk versiyonu oluşturun
git commit -m "İlk yükleme: Proje temizlendi ve hazırlandı"

# 4. Uzak sunucuyu ekleyin (GitHub'dan aldığınız URL'yi yapıştırın)
# ÖRNEK: git remote add origin https://github.com/KULLANICI_ADINIZ/REPO_ADINIZ.git
git remote add origin https://github.com/KULLANICI_ADINIZ/REPO_ADINIZ.git

# 5. Projeyi gönderin
git branch -M main
git push -u origin main
```

## Alternatif: GitHub Desktop ile Yükleme
Komut satırı kullanmak istemezseniz:
1. [GitHub Desktop](https://desktop.github.com/) uygulamasını indirin.
2. Uygulamada **File** -> **Add Local Repository** seçeneğine tıklayın.
3. Bu proje klasörünü (`.../passcore/passcore`) seçin.
4. "This directory does not appear to be a Git repository" uyarısı çıkarsa **Create a Repository** linkine tıklayın.
5. **Publish repository** butonuna tıklayarak GitHub'a gönderin.

---
**Not:** Proje içindeki tüm hassas bilgiler (IP adresleri, şirket isimleri, şifreler) temizlenmiştir. Gönül rahatlığıyla yükleyebilirsiniz.
