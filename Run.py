#!/usr/bin/python3
# -*- coding: utf-8 -*-

import re
import os
import sys
import time
import subprocess

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def install_package(package):
    try:
        __import__(package)
    except ImportError:
        clear_screen()
        print(f"Installing Packages {package}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

required_packages = ['beautifulsoup4', 'requests', 'colorama', 'tqdm']

for package in required_packages:
    if package == 'beautifulsoup4':
        try:
            import bs4
        except ImportError:
            install_package(package)
    else:
        install_package(package)

import requests
import urllib.parse
from tqdm import tqdm
from bs4 import BeautifulSoup
from colorama import Fore, Style
        
FOLDER_DOWNLOAD = '/sdcard/Download/MediaDownloader'

def ensure_download_folder():
    if not os.path.exists(FOLDER_DOWNLOAD):
        try:
            os.makedirs(FOLDER_DOWNLOAD, exist_ok=True)
            print(f'{Fore.GREEN}Folder Download Berhasil Dibuat: {FOLDER_DOWNLOAD}{Style.RESET_ALL}')
            
        except Exception as e:
            print(f'{Fore.RED}Gagal Membuat Folder Download: {e}{Style.RESET_ALL}')
            return False
    return True
    
def trigger_media_scan(file_path):
    try:
        subprocess.run([
            'am', 'broadcast', 
            '-a', 'android.intent.action.MEDIA_SCANNER_SCAN_FILE',
            '-d', f'file://{file_path}'
        ], check=False, capture_output=True)
    except:
        pass
    
    try:
        subprocess.run([
            'am', 'broadcast',
            '-a', 'android.intent.action.MEDIA_MOUNTED',
            '-d', f'file://{os.path.dirname(file_path)}'
        ], check=False, capture_output=True)
    except:
        pass

def download_file(url, filename, platform):
    try:
        if not ensure_download_folder():
            return
            
        response = requests.get(url, stream=True)
        response.raise_for_status()
        total_size = int(response.headers.get('Content-Length', 0))
        
        with open(filename, 'wb') as f:
            progress_bar = tqdm(total=total_size, unit='B', unit_scale=True, colour='green')
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
                    progress_bar.update(len(chunk))
            progress_bar.close()       
            
            trigger_media_scan(filename)         
            
        print(f'{Fore.GREEN}{Style.BRIGHT}Video {platform} Berhasil Diunduh!{Style.RESET_ALL}')
        time.sleep(1.5)
        print(f'{Fore.CYAN}{Style.BRIGHT}Tersimpan Di: {filename}{Style.RESET_ALL}')
        input(f'{Fore.WHITE}{Style.BRIGHT}Tekan Enter untuk kembali ke menu...{Style.RESET_ALL}')
        
    except requests.HTTPError as http_err:
        print(f'{Fore.RED}{Style.BRIGHT}Terjadi Kesalahan HTTP: {http_err}{Style.RESET_ALL}')
        input(f'{Fore.WHITE}{Style.BRIGHT}Tekan Enter untuk kembali ke menu...{Style.RESET_ALL}')
        
    except Exception as err:
        print(f'{Fore.RED}{Style.BRIGHT}Terjadi Kesalahan: {err}{Style.RESET_ALL}')
        input(f'{Fore.WHITE}{Style.BRIGHT}Tekan Enter untuk kembali ke menu...{Style.RESET_ALL}')

def decode_fsve(args):
    if len(args) < 6:
        return ""
    
    h, u, n, t, e, r = args[0], args[1], args[2], int(args[3]), int(args[4]), ""
    
    def decode(d, e, f):
        g = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ+/'
        h_chars = g[:e] 
        i_chars = g[:f]
        j = 0
        
        for c, b in enumerate(reversed(d)):
            if b in h_chars:
                j += h_chars.index(b) * (e ** c)
        
        k = ''
        while j > 0:
            k = i_chars[j % f] + k
            j = (j - (j % f)) // f
        return k if k else '0'
    
    result = ''
    i = 0
    
    while i < len(h):
        s = ''
        while i < len(h) and h[i] != n[e]:
            s += h[i]
            i += 1
        
        for j in range(len(n)):
            s = s.replace(n[j], str(j))
        
        if s:
            try:
                decoded_val = int(decode(s, e, 10)) - t
                if 0 <= decoded_val <= 1114111:
                    result += chr(decoded_val)                   
                    
            except (ValueError, OverflowError):
                pass
        i += 1
    
    try:
        return urllib.parse.unquote(result.encode('utf-8').decode('utf-8'))
    except:
        return result

def get_encoded_fsve(data):
    patterns = [
        r'decodeURIComponent\(escape\(r\)\)\}\((.*?)\)\)',
        r'}\((.*?)\)\)',
        r'return decodeURIComponent\(escape\(r\)\)}\((.*?)\)\)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, data, re.DOTALL)
        if match:
            params_str = match.group(1)
            try:
                params = []
                temp_params = params_str.split(',')
                for p in temp_params:
                    clean_param = p.strip().strip('"').strip("'")
                    params.append(clean_param)
                    
                if len(params) >= 6:
                    return params
            except:
                continue
    return None

def get_decoded_fsave(data):
    patterns = [
        r'getElementById\("download-section"\)\.innerHTML = "(.*?)"; document\.getElementById\("inputData"\)\.remove\(\);',
        r'getElementById\("download-section"\)\.innerHTML="(.*?)";',
        r'innerHTML\s*=\s*"(.*?)"',
        r'"download-section".*?"(.*?)"'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, data, re.DOTALL)
        if match:
            result = match.group(1)
            result = result.replace('\\\\', '\\').replace('\\"', '"').replace("\\'", "'")
            result = re.sub(r'\\(.)', r'\1', result)
            return result
    return data

def decrypt_fsave(data):
    try:
        encoded_params = get_encoded_fsve(data)
        if encoded_params and len(encoded_params) >= 6:
            decoded = decode_fsve(encoded_params)
            if decoded:
                return get_decoded_fsave(decoded)
    except Exception as e:
        pass
        
    return get_decoded_fsave(data)

def decrypt(url):
    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'content-type': 'application/x-www-form-urlencoded',
        'origin': 'https://fsave.io',
        'referer': 'https://fsave.io',
        'user-agent': 'okhttp/4.12.0'
    }
    
    response = requests.post('https://fsave.io/action.php?lang=en', 
                           headers=headers, 
                           data={'url': url})
    
    return decrypt_fsave(response.text)

def tiktok_download(url):
    try:
        print(f'{Fore.YELLOW}{Style.BRIGHT}Memproses URL Video TikTok...{Style.RESET_ALL}')
        decoded_html = decrypt(url)
        if not decoded_html:
            return None
            
        soup = BeautifulSoup(decoded_html, 'html.parser')
        video_02 = ''
        video_01 = ''
        
        table = soup.find('table', class_='table')
        if table:
            tbody = table.find('tbody')
            if tbody:
                rows = tbody.find_all('tr')
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 2:
                        server = cells[0].get_text(strip=True)
                        
                        link = cells[1].find('a')
                        video_url = ''
                        if link and link.get('href'):
                            video_url = link['href']
                        else:
                            button = cells[1].find('button')
                            if button and button.get('onclick'):
                                onclick = button['onclick']
                                match = re.search(r'video_url=([^&\']+)', onclick)
                                if match:
                                    video_url = urllib.parse.unquote(match.group(1))
                                else:
                                    match = re.search(r'get_progressApi\(\'([^\']+)\'', onclick)
                                    if match:
                                        video_url = 'https://fsave.io' + match.group(1)
                        
                        if video_url:
                            if 'Server 01' in server:
                                video_02 = video_url
                            elif 'Server 02' in server:
                                video_01 = video_url
                            else:
                                if not video_01:
                                    video_01 = video_url
                                elif not video_02:
                                    video_02 = video_url
        
        if not video_02 and not video_01:
            download_btns = soup.find_all('a', href=True)
            for btn in download_btns:
                href = btn.get('href', '')
                if 'download' in href:
                    if not href.startswith('http'):
                        href = 'https://fsave.io' + href
                        
                    if not video_01:
                        video_01 = href
                    elif not video_02:
                        video_02 = href
        
        result_url = video_02 or video_01
        return result_url
        
    except Exception as e:
        return None

def facebook_download(url):
    try:
        print(f'{Fore.YELLOW}{Style.BRIGHT}Memproses URL Video Facebook...{Style.RESET_ALL}')
        decoded_html = decrypt(url)
        if not decoded_html:
            return None
            
        soup = BeautifulSoup(decoded_html, 'html.parser')
        video_02 = ''
        video_01 = ''
        
        table = soup.find('table', class_='table')
        if table:
            tbody = table.find('tbody')
            if tbody:
                rows = tbody.find_all('tr')
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 3:
                        resolution = cells[0].get_text(strip=True)
                        
                        link = cells[2].find('a')
                        video_url = ''
                        if link and link.get('href'):
                            video_url = link['href']
                        else:
                            button = cells[2].find('button')
                            if button and button.get('onclick'):
                                onclick = button['onclick']
                                match = re.search(r'video_url=([^&\']+)', onclick)
                                if match:
                                    video_url = urllib.parse.unquote(match.group(1))
                                else:
                                    match = re.search(r'get_progressApi\(\'([^\']+)\'', onclick)
                                    if match:
                                        video_url = 'https://fsave.io' + match.group(1)
                        
                        if video_url:
                            if '720p' in resolution:
                                video_02 = video_url
                            elif '360p' in resolution:
                                video_01 = video_url
        
        if not video_02 and not video_01:
            download_items = soup.find_all('div', class_='download-items__btn')
            for item in download_items:
                link = item.find('a')
                if link and link.get('href'):
                    video_url = link['href']
                    if not video_url.startswith('http'):
                        video_url = f'https://fsave.io/{video_url}'
                    
                    resolution_elem = item.find_parent().find('div', class_='download-items__title')
                    resolution_text = resolution_elem.text if resolution_elem else ''
                    
                    if '720p' in resolution_text:
                        video_02 = video_url
                    elif '360p' in resolution_text:
                        video_01 = video_url
                    elif not video_01:
                        video_01 = video_url
                    elif not video_02:
                        video_02 = video_url
        
        result_url = video_02 or video_01
        return result_url
        
    except Exception as e:
        return None

def instagram_download(url):
    try:
        print(f'{Fore.YELLOW}{Style.BRIGHT}Memproses URL Media Instagram...{Style.RESET_ALL}')
        decoded_html = decrypt(url)
        if not decoded_html:
            return []
            
        soup = BeautifulSoup(decoded_html, 'html.parser')
        media_items = []
        
        download_items = soup.find_all('div', class_='download-items')
        for i, item in enumerate(download_items):
            thumb_img = item.find('div', class_='download-items__thumb')
            if thumb_img:
                img_elem = thumb_img.find('img')
                thumb_url = img_elem.get('src', '') if img_elem else ''
            else:
                thumb_url = ''
            
            buttons = item.find_all('div', class_='download-items__btn')
            for btn in buttons:
                link = btn.find('a')
                if link and link.get('href'):
                    media_url = link['href']
                    if not media_url.startswith('http'):
                        media_url = f'https://fsave.io/{media_url}'
                    
                    btn_text = btn.get_text(strip=True).lower()
                    
                    if 'photo' in btn_text or 'image' in btn_text or 'jpg' in btn_text:
                        media_type = 'image'
                        extension = '.jpg'
                    else:
                        media_type = 'video'
                        extension = '.mp4'
                    
                    media_items.append({
                        'url': media_url,
                        'thumb': thumb_url,
                        'type': media_type,
                        'extension': extension,
                        'index': i + 1
                    })
        
        return media_items
        
    except Exception as e:
        return []

def download_instagram_media(media_items, base_url):
    if not media_items:
        print(f'{Fore.RED}{Style.BRIGHT}Tidak Ada Media Instagram Yang Ditemukan!{Style.RESET_ALL}')
        input(f'{Fore.WHITE}{Style.BRIGHT}Tekan Enter untuk kembali ke menu...{Style.RESET_ALL}')
        return
    
    print(f'{Fore.GREEN}{Style.BRIGHT}Ditemukan {len(media_items)} Media{Style.RESET_ALL}')
    
    error_occurred = False
    downloaded_files = []
    
    for media in media_items:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(FOLDER_DOWNLOAD, f'Instagram_{timestamp}_{media["index"]}{media["extension"]}')
        
        print(f'{Fore.CYAN}{Style.BRIGHT}Mengunduh {media["type"]} {media["index"]}/{len(media_items)}...{Style.RESET_ALL}')
        
        try:
            if not ensure_download_folder():
                error_occurred = True
                continue
                
            response = requests.get(media['url'], stream=True)
            response.raise_for_status()
            total_size = int(response.headers.get('Content-Length', 0))
            
            with open(filename, 'wb') as f:
                progress_bar = tqdm(total=total_size, unit='B', unit_scale=True, colour='green', desc=f'{media["type"]} {media["index"]}')
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
                        progress_bar.update(len(chunk))
                progress_bar.close()
                
                trigger_media_scan(filename)
                
            print(f'{Fore.GREEN}{Style.BRIGHT}{media["type"].capitalize()} {media["index"]} Berhasil Diunduh!{Style.RESET_ALL}')
            time.sleep(1.5)
            print(f'{Fore.BLUE}{Style.BRIGHT}Tersimpan Di: {filename}{Style.RESET_ALL}')
            downloaded_files.append(filename)
            time.sleep(0.5)
            
        except Exception as e:
            print(f'{Fore.RED}{Style.BRIGHT}Error Mengunduh {media["type"]} {media["index"]}: {e}{Style.RESET_ALL}')
            error_occurred = True
    
    if not error_occurred and downloaded_files:
        time.sleep(0.5)
    
    input(f'{Fore.WHITE}{Style.BRIGHT}Tekan Enter untuk kembali ke menu...{Style.RESET_ALL}')

def is_valid_url(url, pattern):
    return re.match(pattern, url) is not None

def menu():
    clear_screen()
    print('')
    print(f'{Fore.CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Style.RESET_ALL}')
    print(f'{Fore.WHITE}     • MEDIA DOWNLOADER MENU •       {Style.RESET_ALL}')
    print(f'{Fore.CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Style.RESET_ALL}')
    print(f'{Fore.GREEN}[1]{Style.RESET_ALL} TikTok Video')
    print(f'{Fore.GREEN}[2]{Style.RESET_ALL} Facebook Video')
    print(f'{Fore.GREEN}[3]{Style.RESET_ALL} Instagram Media (Video/Photo)')
    print(f'{Fore.RED}[0]{Style.RESET_ALL} Keluar')
    print(f'{Fore.CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Style.RESET_ALL}')

def RSCoders():
    tiktok_pattern = r'^https://.*tiktok\.com/.+'
    facebook_pattern = r'^https://.*facebook\.com/.+'
    instagram_pattern = r'^https://.*instagram\.com/.+'

    while True:
        try:
            menu()
            choice = input('Masukkan Pilihan [1-3/0]: ')
            
            if choice == '1':
                url = input(f'{Fore.BLUE}{Style.BRIGHT}Masukkan URL Video TikTok: {Style.RESET_ALL}')       
                if is_valid_url(url, tiktok_pattern):
                    video_url = tiktok_download(url)
                    if video_url:
                        video_filename = os.path.join(FOLDER_DOWNLOAD, f'TikTok_{time.strftime("%Y%m%d_%H%M%S")}.mp4')
                        download_file(video_url, video_filename, 'TikTok')
                    else:
                        print(f'{Fore.RED}{Style.BRIGHT}Gagal Mendapatkan Data Dari URL Video TikTok.{Style.RESET_ALL}')
                        input(f'{Fore.WHITE}{Style.BRIGHT}Tekan Enter untuk kembali ke menu...{Style.RESET_ALL}')
                else:
                    print(f'{Fore.RED}{Style.BRIGHT}URL TikTok Tidak Valid.{Style.RESET_ALL}')
                    input(f'{Fore.WHITE}{Style.BRIGHT}Tekan Enter untuk kembali ke menu...{Style.RESET_ALL}')
                    
            elif choice == '2':
                url = input(f'{Fore.BLUE}{Style.BRIGHT}Masukkan URL Video Facebook: {Style.RESET_ALL}')
                if is_valid_url(url, facebook_pattern):
                    video_url = facebook_download(url)
                    if video_url:
                        video_filename = os.path.join(FOLDER_DOWNLOAD, f'Facebook_{time.strftime("%Y%m%d_%H%M%S")}.mp4')
                        download_file(video_url, video_filename, 'Facebook')
                    else:
                        print(f'{Fore.RED}{Style.BRIGHT}Gagal Mendapatkan Data Dari URL Video Facebook.{Style.RESET_ALL}')
                        input(f'{Fore.WHITE}{Style.BRIGHT}Tekan Enter untuk kembali ke menu...{Style.RESET_ALL}')
                else:
                    print(f'{Fore.RED}{Style.BRIGHT}URL Facebook Tidak Valid.{Style.RESET_ALL}')
                    input(f'{Fore.WHITE}{Style.BRIGHT}Tekan Enter untuk kembali ke menu...{Style.RESET_ALL}')
                    
            elif choice == '3':
                url = input(f'{Fore.BLUE}{Style.BRIGHT}Masukkan URL Media Instagram: {Style.RESET_ALL}')
                if is_valid_url(url, instagram_pattern):
                    media_items = instagram_download(url)
                    if media_items:
                        download_instagram_media(media_items, url)
                    else:
                        print(f'{Fore.RED}{Style.BRIGHT}Gagal Mendapatkan Data Dari URL Media Instagram.{Style.RESET_ALL}')
                        input(f'{Fore.WHITE}{Style.BRIGHT}Tekan Enter untuk kembali ke menu...{Style.RESET_ALL}')
                else:
                    print(f'{Fore.RED}{Style.BRIGHT}URL Instagram Tidak Valid.{Style.RESET_ALL}')
                    input(f'{Fore.WHITE}{Style.BRIGHT}Tekan Enter untuk kembali ke menu...{Style.RESET_ALL}')
                    
            elif choice == '0':
                print(f'{Fore.BLUE}{Style.BRIGHT}Keluar...{Style.RESET_ALL}')
                time.sleep(1.5)
                exit(0)
                
            else:
                print(f'{Fore.RED}{Style.BRIGHT}Pilihan Tidak Valid!{Style.RESET_ALL}')
                input(f'{Fore.WHITE}{Style.BRIGHT}Tekan Enter untuk kembali ke menu...{Style.RESET_ALL}')
                
        except KeyboardInterrupt:
            print(f'\n{Fore.YELLOW}Program Telah Dihentikan.{Style.RESET_ALL}')
            exit(0)
            
        except Exception as e:
            print(f'{Fore.RED}{Style.BRIGHT}Terjadi Kesalahan: {e}{Style.RESET_ALL}')
            input(f'{Fore.WHITE}{Style.BRIGHT}Tekan Enter untuk kembali ke menu...{Style.RESET_ALL}')

if __name__ == "__main__":
    RSCoders()