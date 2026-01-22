"""
Web Scraper Module for RAG enrichment.
Scrapes web pages, extracts text and images, and prepares data for indexing.
"""

import os
import re
import time
import hashlib
import requests
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from langchain_core.documents import Document

# Default headers to mimic a browser
DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}


class WebScraper:
    """
    Scrapes web pages and extracts content for RAG indexing.
    Supports text extraction, image collection, and link discovery.
    """
    
    def __init__(self, timeout: int = 30, delay: float = 1.0):
        """
        Initialize the web scraper.
        
        Args:
            timeout: Request timeout in seconds
            delay: Delay between requests (be polite to servers)
        """
        self.timeout = timeout
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        self.scraped_urls = set()  # Track scraped URLs to avoid duplicates
        
    def scrape_url(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Scrape a single URL and extract its content.
        
        Args:
            url: The URL to scrape
            
        Returns:
            Dictionary with extracted content or None if failed
        """
        if url in self.scraped_urls:
            print(f"⏭️ Skipping already scraped: {url}")
            return None
            
        print(f"🌐 Scraping: {url}")
        
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            # Mark as scraped
            self.scraped_urls.add(url)
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract content
            result = {
                'url': url,
                'status_code': response.status_code,
                'title': self._extract_title(soup),
                'text': self._extract_text(soup),
                'images': self._extract_images(soup, url),
                'links': self._extract_links(soup, url),
                'meta_description': self._extract_meta_description(soup),
                'html_raw': response.text[:50000],  # Limit raw HTML size
                'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            }
            
            print(f"  ✅ Extracted: {len(result['text'])} chars, {len(result['images'])} images, {len(result['links'])} links")
            
            # Polite delay
            time.sleep(self.delay)
            
            return result
            
        except requests.RequestException as e:
            print(f"  ❌ Failed to scrape {url}: {e}")
            return None
    
    def scrape_multiple(self, urls: List[str], follow_links: bool = False, max_pages: int = 10) -> List[Dict[str, Any]]:
        """
        Scrape multiple URLs.
        
        Args:
            urls: List of URLs to scrape
            follow_links: If True, also scrape internal links found (up to max_pages)
            max_pages: Maximum number of pages to scrape
            
        Returns:
            List of scraped content dictionaries
        """
        results = []
        to_scrape = list(urls)
        base_domains = {urlparse(url).netloc for url in urls}
        
        while to_scrape and len(results) < max_pages:
            url = to_scrape.pop(0)
            
            result = self.scrape_url(url)
            if result:
                results.append(result)
                
                # Optionally follow internal links
                if follow_links and len(results) < max_pages:
                    for link in result.get('links', []):
                        link_domain = urlparse(link).netloc
                        if link_domain in base_domains and link not in self.scraped_urls:
                            if link not in to_scrape:
                                to_scrape.append(link)
        
        print(f"\n📊 Scraping complete: {len(results)} pages scraped")
        return results
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract page title."""
        title_tag = soup.find('title')
        if title_tag:
            return title_tag.get_text(strip=True)
        
        h1_tag = soup.find('h1')
        if h1_tag:
            return h1_tag.get_text(strip=True)
            
        return "Untitled Page"
    
    def _extract_text(self, soup: BeautifulSoup) -> str:
        """Extract clean text content from the page."""
        # Remove unwanted elements
        for element in soup.find_all(['script', 'style', 'nav', 'footer', 'header', 'aside', 'noscript']):
            element.decompose()
        
        # Try to find main content area
        main_content = soup.find('main') or soup.find('article') or soup.find('div', {'class': re.compile(r'content|main|article', re.I)})
        
        if main_content:
            text = main_content.get_text(separator='\n', strip=True)
        else:
            text = soup.get_text(separator='\n', strip=True)
        
        # Clean up whitespace
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        text = '\n'.join(lines)
        
        # Remove excessive whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text
    
    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
        """Extract image URLs and alt text."""
        images = []
        
        for img in soup.find_all('img'):
            src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
            if not src:
                continue
                
            # Convert relative URLs to absolute
            src = urljoin(base_url, src)
            
            # Skip data URIs and tiny images (likely icons)
            if src.startswith('data:'):
                continue
                
            images.append({
                'url': src,
                'alt': img.get('alt', ''),
                'title': img.get('title', ''),
            })
        
        return images
    
    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract internal links from the page."""
        links = []
        base_domain = urlparse(base_url).netloc
        
        for a in soup.find_all('a', href=True):
            href = a['href']
            
            # Skip anchors, javascript, mailto, etc.
            if href.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                continue
            
            # Convert to absolute URL
            full_url = urljoin(base_url, href)
            
            # Only include links from the same domain
            if urlparse(full_url).netloc == base_domain:
                # Clean URL (remove fragments)
                clean_url = full_url.split('#')[0]
                if clean_url and clean_url not in links:
                    links.append(clean_url)
        
        return links
    
    def _extract_meta_description(self, soup: BeautifulSoup) -> str:
        """Extract meta description."""
        meta = soup.find('meta', attrs={'name': 'description'})
        if meta:
            return meta.get('content', '')
        return ""


class WebToDocuments:
    """
    Converts scraped web content to LangChain Documents for RAG indexing.
    """
    
    def __init__(self):
        self.scraper = WebScraper()
    
    def scrape_and_convert(
        self, 
        urls: List[str], 
        follow_links: bool = False,
        max_pages: int = 10,
        include_images: bool = True
    ) -> Tuple[List[Document], List[Dict[str, Any]]]:
        """
        Scrape URLs and convert to LangChain Documents.
        
        Args:
            urls: List of URLs to scrape
            follow_links: Whether to follow internal links
            max_pages: Maximum pages to scrape
            include_images: Whether to include image metadata in documents
            
        Returns:
            Tuple of (documents for text, image_data for separate processing)
        """
        print(f"🚀 Starting web scraping for {len(urls)} URL(s)...")
        
        # Scrape the pages
        scraped_data = self.scraper.scrape_multiple(urls, follow_links, max_pages)
        
        documents = []
        all_images = []
        
        for data in scraped_data:
            # Create main document for text content
            if data['text']:
                content = f"# {data['title']}\n\n{data['text']}"
                
                # Add meta description if available
                if data['meta_description']:
                    content = f"# {data['title']}\n\n**Description**: {data['meta_description']}\n\n{data['text']}"
                
                doc = Document(
                    page_content=content,
                    metadata={
                        'source': data['url'],
                        'title': data['title'],
                        'type': 'web_page',
                        'scraped_at': data['scraped_at'],
                        'image_count': len(data['images']),
                        'link_count': len(data['links']),
                    }
                )
                documents.append(doc)
            
            # Collect image data
            if include_images:
                for img in data['images']:
                    img['source_page'] = data['url']
                    img['page_title'] = data['title']
                    all_images.append(img)
                    
                    # Create a document for images with alt text
                    if img['alt']:
                        img_doc = Document(
                            page_content=f"Image on page '{data['title']}': {img['alt']}",
                            metadata={
                                'source': data['url'],
                                'image_url': img['url'],
                                'type': 'web_image',
                            }
                        )
                        documents.append(img_doc)
        
        print(f"📄 Created {len(documents)} documents from {len(scraped_data)} pages")
        print(f"🖼️ Found {len(all_images)} images total")
        
        return documents, all_images
    
    def download_images(self, images: List[Dict[str, str]], output_dir: str = "scraped_images") -> List[str]:
        """
        Download images to local directory.
        
        Args:
            images: List of image dictionaries with 'url' key
            output_dir: Directory to save images
            
        Returns:
            List of local file paths
        """
        os.makedirs(output_dir, exist_ok=True)
        downloaded = []
        
        for img in images:
            try:
                url = img['url']
                
                # Generate filename from URL hash
                ext = os.path.splitext(urlparse(url).path)[1] or '.jpg'
                filename = hashlib.md5(url.encode()).hexdigest()[:12] + ext
                filepath = os.path.join(output_dir, filename)
                
                # Skip if already downloaded
                if os.path.exists(filepath):
                    downloaded.append(filepath)
                    continue
                
                # Download image
                response = requests.get(url, timeout=15)
                response.raise_for_status()
                
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                
                downloaded.append(filepath)
                print(f"  📥 Downloaded: {filename}")
                
            except Exception as e:
                print(f"  ⚠️ Failed to download {img.get('url', 'unknown')}: {e}")
        
        return downloaded


def scrape_urls_for_rag(
    urls: List[str],
    follow_links: bool = False,
    max_pages: int = 10,
    include_images: bool = True
) -> Tuple[List[Document], List[Dict[str, Any]]]:
    """
    Convenience function to scrape URLs and get documents ready for RAG.
    
    Args:
        urls: List of URLs to scrape
        follow_links: Whether to follow internal links
        max_pages: Maximum pages to scrape
        include_images: Whether to process images
        
    Returns:
        Tuple of (documents, image_data)
    """
    converter = WebToDocuments()
    return converter.scrape_and_convert(urls, follow_links, max_pages, include_images)
