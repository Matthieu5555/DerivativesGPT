#!/usr/bin/env python3

"""
Stage 1: Aggressive Chapter Detection for OCR'd Academic Books
Enhanced with intelligent gap labeling for undetected chapters
"""

import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional, NamedTuple
import yaml
from dataclasses import dataclass, asdict
import json
from difflib import SequenceMatcher
import math # Added for position_percent calculation

# ============================================================================
# CONFIGURATION
# ============================================================================

# Hardcoded variables should be at the top and clearly identified.
INPUT_DIR = Path("rag/chunking/documents")
YAML_FILE = Path("rag/chunking/documents/manual_chapters.yaml")
OUTPUT_DIR = Path("data/chunking_stages/stage_1_basic_chunks")

CHUNK_SIZE = 2000
MIN_CHUNK_SIZE = 500
TOC_ANALYSIS_RANGE_RATIO = 0.15 
TOC_CONTEXT_WINDOW = 1000

# Global variable to avoid a runtime error in main
INPUT_LOGIC_DIR: Path = INPUT_DIR

# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class ChapterBoundary:
    """Represents a detected chapter"""
    chapter_num: int
    title: str
    start_pos: int
    end_pos: Optional[int] = None
    confidence: float = 1.0
    detection_method: str = "unknown"

@dataclass
class BookBoundaries:
    """Complete book structure"""
    book_name: str
    book_start: int
    book_end: int
    chapters: List[ChapterBoundary]
    detection_stats: Dict

@dataclass
class Chunk:
    """A chunk of text with metadata"""
    chunk_id: str
    book_name: str
    chapter_number: Optional[int]
    chapter_title: Optional[str]
    chunk_index_in_chapter: int
    total_chunks_in_chapter: int
    text: str
    char_start: int
    char_end: int
    chunking_method: str
    # NEW: Added required fields for Stage 2 alignment
    confidence: float # Confidence in chapter/gap detection
    position_percent: float # Position in book as percentage

# ============================================================================
# CHAPTER DETECTION STRATEGIES
# ============================================================================

class ChapterDetector:
    """Multi-strategy chapter detection"""

    # Escaped '##' in the regex for re.VERBOSE compatibility
    _chapter_num_regex = re.compile(
        r"""
        (?:Chapter|CHAPTER|\#\#)\s*(\d+)(?![0-9.])\b | # 'Chapter 5' or '## 5'
        (?:^|\n)\s*(\d+)(?![0-9.])\.\s+             # '5. '
        """,
        re.VERBOSE | re.MULTILINE
    )

    def __init__(
        self, 
        text: str, 
        chapter_titles: List[str], 
        book_start_pos: int, 
        book_end_pos: int,
        front_matter_boundary: int
    ):
        self.text = text
        self.chapter_titles = chapter_titles
        self.text_lower = text.lower()
        self.book_start_pos = book_start_pos
        self.book_end_pos = book_end_pos 
        self.front_matter_boundary = front_matter_boundary
        self.book_length = len(text)
        
        self.toc_boundary = min(
            self.book_length * TOC_ANALYSIS_RANGE_RATIO, 
            self.book_end_pos
        )

        self.normalized_titles = [
            self._normalize_text(title) for title in chapter_titles
        ]

    def detect_all_chapters(self) -> List[ChapterBoundary]:
        """Try multiple detection strategies in order of reliability"""
        strategies = [
            ("missing_page_heuristic", self.strategy_missing_page_heuristic),
            ("partial_title_markdown", self.strategy_partial_title_markdown),
            ("high_confidence_markdown", self.strategy_high_confidence_markdown),
            ("subsection_as_chapter", self.strategy_subsection_as_chapter),
            ("exact_with_keyword", self.strategy_exact_with_keyword),
            ("markdown_headers", self.strategy_markdown_headers),
            ("plain_text_with_number", self.strategy_plain_text_with_number),
            ("plain_text_multiline", self.strategy_plain_text_multiline),
            ("numbered_patterns", self.strategy_numbered_patterns),
            ("partial_title_only", self.strategy_partial_title_only),
            ("fuzzy_matching", self.strategy_fuzzy_matching),
            ("fuzzy_keyword", self.strategy_fuzzy_keyword),
            ("aggressive_fuzzy", self.strategy_aggressive_fuzzy),
        ]

        all_candidates = []
        already_found = set()

        print("    Running detection strategies...")
        for strategy_name, strategy_func in strategies:
            candidates = strategy_func()

            for candidate in candidates:
                if candidate.chapter_num in already_found:
                    continue

                if self._validate_position(candidate, all_candidates):
                    candidate.detection_method = strategy_name
                    all_candidates.append(candidate)
                    already_found.add(candidate.chapter_num)

        all_candidates.sort(key=lambda x: x.start_pos)
        
        # --- GAP-FILLING STEP ---
        gap_finds = self.strategy_search_gaps(all_candidates)
        
        if gap_finds:
            print(f"            ✓ Gap-filler found {len(gap_finds)} new chapter(s).")
            for new_ch in gap_finds:
                if new_ch.chapter_num not in already_found:
                    all_candidates.append(new_ch)
                    already_found.add(new_ch.chapter_num)
        
        # --- TOC FILTERING STEP ---
        print("    Filtering Table of Contents matches...")
        filtered_chapters = self._filter_toc_entries(all_candidates)

        filtered_chapters.sort(key=lambda x: x.start_pos)

        print("    Detection run complete.")
        for ch in filtered_chapters:
            preview = self.text[ch.start_pos:ch.start_pos + 80].replace('\n', ' ')
            print(f"            ✓ Chapter {ch.chapter_num}: Found at {ch.start_pos} (via {ch.detection_method})")
            print(f"            Preview: '{preview[:60]}...'")

        for i in range(len(filtered_chapters) - 1):
            filtered_chapters[i].end_pos = filtered_chapters[i + 1].start_pos
        if filtered_chapters:
            filtered_chapters[-1].end_pos = self.book_end_pos

        return filtered_chapters
    
    def _validate_and_extract_chapter_num(
        self, 
        match_text: str, 
        expected_idx: int
    ) -> Optional[int]:
        """Parses text to find a chapter number and validates it against the expected index."""
        
        # 1. Check for a CLEAN chapter number
        clean_match = self._chapter_num_regex.search(match_text)
        if clean_match:
            found_num_str = clean_match.group(1) or clean_match.group(2) 
            if found_num_str:
                try:
                    found_num = int(found_num_str)
                    return found_num if found_num == expected_idx else None
                except ValueError:
                    pass 

        # 2. Check for a SUB-SECTION 
        subsection_match = re.search(r'\b(\d+)(?:\.\d+)+\b', match_text)
        if subsection_match:
            return None 
        
        # 3. Check for a simple number (close to the start)
        simple_num_match = re.search(r'\b(\d+)\b', match_text)
        if simple_num_match:
            if simple_num_match.start() < 10: 
                try:
                    found_num = int(simple_num_match.group(1))
                    return found_num if found_num == expected_idx else None
                except ValueError:
                    pass
        
        # 4. Pure title match is acceptable if no contradicting number is found
        return expected_idx

    def _filter_toc_entries(self, candidates: List[ChapterBoundary]) -> List[ChapterBoundary]:
        """Filters out candidates that are likely from a Table of Contents."""
        final_chapters = []
        chapters_by_num: Dict[int, List[ChapterBoundary]] = {}

        for c in candidates:
            if c.chapter_num not in chapters_by_num:
                chapters_by_num[c.chapter_num] = []
            chapters_by_num[c.chapter_num].append(c)

        for chapter_num, matches in chapters_by_num.items():
            if not matches:
                continue
            matches.sort(key=lambda x: x.start_pos)
            
            selected_match = None
            for match in matches:
                if not self._is_likely_toc_entry(match):
                    selected_match = match
                    break
            
            if selected_match is None:
                # Fallback: take the last (i.e., furthest down the book) match
                selected_match = matches[-1] 
            
            final_chapters.append(selected_match)

        return final_chapters
    
    def _is_likely_toc_entry(self, candidate: ChapterBoundary) -> bool:
        """Checks if a candidate is a TOC entry."""
        is_in_suspect_zone = (candidate.start_pos < self.front_matter_boundary or 
                              candidate.start_pos < self.toc_boundary)
        
        if not is_in_suspect_zone:
            return False

        # Heuristic 1: Check for dot-leader pattern (TOC hallmark)
        try:
            line_end_pos = self.text.index('\n', candidate.start_pos, min(self.book_end_pos, candidate.start_pos + 300))
            context_line = self.text[candidate.start_pos:line_end_pos]
            
            if re.search(r'[\. ]{5,}\s*\d+\s*$', context_line):
                return True 
        except ValueError:
            pass 
        
        # Heuristic 2: Check for next chapter title nearby (TOC hallmark)
        context_start = candidate.start_pos + len(candidate.title)
        context_end = min(self.book_end_pos, context_start + TOC_CONTEXT_WINDOW)
        context = self.text[context_start:context_end]
        
        if context:
            context_norm = self._normalize_text(context)
            next_ch_num = candidate.chapter_num + 1
            next_title = self.chapter_titles[next_ch_num - 1] if len(self.chapter_titles) >= next_ch_num else None
            
            if next_title:
                if self._normalize_text(next_title)[:20] in context_norm:
                    return True

        return False
    
    def _get_partial_title_snippet(self, title: str, num_words: int = 4, min_len: int = 15) -> Optional[str]:
        """Gets the first few significant words of a title."""
        title_words = re.findall(r'\b[A-Za-z]{3,}\b', title)
        if not title_words:
            return None

        partial_title_snippet = " ".join(title_words[:num_words])
        
        if len(partial_title_snippet) < min_len and len(title_words) > num_words:
             partial_title_snippet = " ".join(title_words[:num_words + 1])

        if len(partial_title_snippet) < min_len:
            return None
            
        return partial_title_snippet
    
    def strategy_missing_page_heuristic(self) -> List[ChapterBoundary]:
        """Looks for '[MISSING_PAGE...]' followed by a title on a new line."""
        candidates = []
        for idx, title in enumerate(self.chapter_titles, 1):
            snippet = self._get_partial_title_snippet(title, num_words=3, min_len=10)
            if not snippet:
                continue
            pattern = rf"\[MISSING_PAGE_EMPTY:\d+\]\s*(?:\n\s*){{0,3}}{re.escape(snippet)}"
            if self._find_match(pattern, idx, title, 0.98, candidates, re.IGNORECASE):
                break
        return candidates

    def strategy_partial_title_markdown(self) -> List[ChapterBoundary]:
        """Looks for '## [Num] [First Few Words of Title]'"""
        candidates = []
        for idx, title in enumerate(self.chapter_titles, 1):
            snippet = self._get_partial_title_snippet(title)
            if not snippet:
                continue
            patterns = [
                rf"(?:^|\n)\s*(##+)\s*{idx}\s*[:\.\-]?\s*{re.escape(snippet)}",
                rf"(?:^|\n)\s*(##+)\s*(?:Chapter|CHAPTER)\s+{idx}\s*[:\.\-]?\s*{re.escape(snippet)}",
            ]
            for p in patterns:
                if self._find_match(p, idx, title, 0.92, candidates, re.IGNORECASE): 
                    break
        return candidates

    def strategy_subsection_as_chapter(self) -> List[ChapterBoundary]:
        """Looks for '## 6.1 [Title]' and counts it as Chapter 6."""
        candidates = []
        for idx, title in enumerate(self.chapter_titles, 1):
            snippet = self._get_partial_title_snippet(title, num_words=3, min_len=10)
            if not snippet:
                continue
            pattern = rf"(?:^|\n)\s*(##+)\s*{idx}\.1\s*[:\.\-]?\s*{re.escape(snippet)}"
            if self._find_match(pattern, idx, title, 0.91, candidates, re.IGNORECASE):
                break
        return candidates

    def strategy_high_confidence_markdown(self) -> List[ChapterBoundary]:
        """Looks for exact '## Chapter [Num] [Title]' patterns."""
        candidates = []
        for idx, title in enumerate(self.chapter_titles, 1):
            patterns = [
                rf"(?:^|\n)\s*(##+)\s*(?:Chapter|CHAPTER)\s+{idx}\s*[:\.\-]?\s*{re.escape(title)}",
                rf"(?:^|\n)\s*(##+)\s*(?:Chapter|CHAPTER)\s+{re.escape(title)}",
                rf"(?:^|\n)\s*(##+)\s*{idx}\s*[:\.\-]?\s*{re.escape(title)}",
            ]
            for p in patterns:
                if self._find_match(p, idx, title, 1.0, candidates, re.IGNORECASE): break
        return candidates

    def strategy_exact_with_keyword(self) -> List[ChapterBoundary]:
        """Look for 'Chapter' or 'CHAPTER' followed by title (more flexible)"""
        candidates = []
        for idx, title in enumerate(self.chapter_titles, 1):
            patterns = [
                rf"(?:^|\n)\s*(?:chapter|CHAPTER)\s+{re.escape(title)}",
                rf"(?:^|\n)\s*(?:chapter|CHAPTER)\s+{idx}[:\s\-\.]*{re.escape(title)}",
                rf"(?:^|\n)\s*{idx}[\.\s\-:]+{re.escape(title)}",
            ]
            for p in patterns:
                if self._find_match(p, idx, title, 0.95, candidates, re.IGNORECASE): break
        return candidates

    def strategy_markdown_headers(self) -> List[ChapterBoundary]:
        """Look for markdown headers with title (no 'Chapter' keyword)"""
        candidates = []
        for idx, title in enumerate(self.chapter_titles, 1):
            patterns = [
                rf"(?:^|\n)(#{1,4})\s*{re.escape(title)}",
                rf"(?:^|\n)(#{1,4})\s*{idx}[\.\s\-:]*{re.escape(title)}",
            ]
            for p in patterns:
                if self._find_match(p, idx, title, 0.9, candidates, re.IGNORECASE): break
        return candidates

    def strategy_plain_text_with_number(self) -> List[ChapterBoundary]:
        """Looks for '1 Title' on a line"""
        candidates = []
        for idx, title in enumerate(self.chapter_titles, 1):
            pattern = rf"(?:^|\n)\s*{idx}\s*[:\.\-]?\s*{re.escape(title)}\s*(?:\n|$)"
            self._find_match(pattern, idx, title, 0.88, candidates, re.IGNORECASE)
        return candidates

    def strategy_plain_text_multiline(self) -> List[ChapterBoundary]:
        """Looks for 'Chapter 1' and 'Title' on separate lines"""
        candidates = []
        for idx, title in enumerate(self.chapter_titles, 1):
            patterns = [
                rf"((?:^|\n)\s*(?:Chapter|CHAPTER)\s+{idx}\s*(?:\n|$))([^\n]*{re.escape(title)})",
                rf"((?:^|\n)\s*{idx}\s*(?:\n|$))([^\n]*{re.escape(title)})",
            ]
            for p in patterns:
                if self._find_match(p, idx, title, 0.87, candidates, re.IGNORECASE): break
        return candidates

    def strategy_numbered_patterns(self) -> List[ChapterBoundary]:
        """Look for chapter numbers with various formatting (partial title)"""
        candidates = []
        for idx, title in enumerate(self.chapter_titles, 1):
            roman_map = {1:'I', 2:'II', 3:'III', 4:'IV', 5:'V', 6:'VI', 7:'VII', 8:'VIII', 9:'IX', 10:'X',
                         11:'XI', 12:'XII', 13:'XIII', 14:'XIV', 15:'XV'}
            roman = roman_map.get(idx, '')
            title_hint = title[:25]
            if len(title_hint) < 10: continue
            patterns = [rf"(?:^|\n)\s*(?:Chapter\s+)?{idx}\s*[:\-\.]\s*{re.escape(title_hint)}"]
            if roman:
                patterns.append(rf"(?:^|\n)\s*(?:Chapter\s+)?{roman}\s*[:\-\.]\s*{re.escape(title_hint)}")
            for p in patterns:
                if self._find_match(p, idx, title, 0.85, candidates, re.IGNORECASE): break
        return candidates

    def strategy_partial_title_only(self) -> List[ChapterBoundary]:
        """Look for title alone on a line (fuzzier, partial match)."""
        candidates = []
        for idx, title in enumerate(self.chapter_titles, 1):
            snippet = self._get_partial_title_snippet(title)
            if not snippet:
                continue
            patterns = [
                rf"(?:^|\n)\s*{re.escape(snippet)}[^\n]*\s*(?:\n|$)",
                rf"(?:^|\n)\s*\**{re.escape(snippet)}[^\n]*\**\s*(?:\n|$)",
            ]
            for p in patterns:
                if self._find_match(p, idx, title, 0.7, candidates, re.IGNORECASE): break
        return candidates

    def strategy_fuzzy_matching(self) -> List[ChapterBoundary]:
        """Fuzzy match for title, BUT validate the chapter number."""
        candidates = []
        for idx, title in enumerate(self.chapter_titles, 1):
            title_norm = self._normalize_text(title)
            title_words = title_norm.split()[:5]
            if len(title_words) < 2: continue
            
            search_pattern = r'(?:^|\n)[^\n]{0,100}' + r'[^\n]{0,20}'.join(re.escape(w) for w in title_words[:3])
            try:
                for match in re.finditer(search_pattern, self.text[:self.book_end_pos], re.IGNORECASE | re.MULTILINE):
                    window_text = self.text[match.start():match.start() + 150]
                    if self._validate_and_extract_chapter_num(window_text, idx) is None:
                        continue
                    similarity = self._calculate_similarity(title, match.group(0))
                    if similarity > 0.75:
                        candidates.append(ChapterBoundary(idx, title, match.start(), confidence=similarity * 0.8))
                        break
            except re.error: continue
        return candidates

    def strategy_fuzzy_keyword(self) -> List[ChapterBoundary]:
        """Fuzzy match by looking for keywords, validating chapter number."""
        candidates = []
        STOPWORDS = set([
            'a', 'an', 'and', 'the', 'in', 'on', 'of', 'for', 'to', 'with', 
            'is', 'are', 'was', 'were', 'it', 'i', 'you', 'he', 'she', 'they'
        ])

        for idx, title in enumerate(self.chapter_titles, 1):
            keywords = [
                w for w in re.findall(r'\b[A-Za-z]+\b', title.lower())
                if len(w) > 3 and w not in STOPWORDS
            ]
            if len(keywords) < 2:
                continue
            target_keywords = set(keywords[:4])

            try:
                search_regex = r'\b' + r'\b.*\b'.join(re.escape(k) for k in target_keywords) + r'\b'
                
                for match in re.finditer(
                    search_regex, 
                    self.text[:self.book_end_pos], 
                    re.IGNORECASE | re.DOTALL
                ):
                    match_text = match.group(0)
                    if len(match_text) > 500:
                        continue 
                    window_text = self.text[match.start():match.start() + 150]
                    if self._validate_and_extract_chapter_num(window_text, idx) is None:
                        continue
                    if self._looks_like_heading(window_text):
                        candidates.append(ChapterBoundary(
                            chapter_num=idx, 
                            title=title, 
                            start_pos=match.start(), 
                            confidence=0.6,
                            detection_method="fuzzy_keyword"
                        ))
                        break 
            except re.error:
                continue
        return candidates

    def strategy_aggressive_fuzzy(self) -> List[ChapterBoundary]:
        """Very aggressive fuzzy matching, validating chapter number."""
        candidates = []
        search_limit = min(self.book_length - 200, self.book_end_pos)
        
        for idx, title in enumerate(self.chapter_titles, 1):
            title_words = re.findall(r'\b[A-Za-z]{4,}\b', title)[:3]
            if not title_words: continue

            for pos in range(0, search_limit, 100):
                window_text = self.text[pos:pos + 200]
                window_lower = window_text.lower()
                words_found = sum(1 for word in title_words if word.lower() in window_lower)
                
                if words_found >= min(2, len(title_words)) and self._looks_like_heading(window_text):
                    if self._validate_and_extract_chapter_num(window_text, idx) is None:
                        continue
                    candidates.append(ChapterBoundary(idx, title, pos, confidence=0.5))
                    break
        return candidates
    
    def strategy_search_gaps(self, found_chapters: List[ChapterBoundary]) -> List[ChapterBoundary]:
        """Searches for missing chapters ONLY in the gaps between found chapters."""
        print("    Running gap-filling strategy...")
        new_finds = []
        found_nums = {ch.chapter_num for ch in found_chapters}
        pos_map = {ch.chapter_num: ch.start_pos for ch in found_chapters}
        pos_map[0] = self.book_start_pos

        if found_chapters:
            last_ch_num = found_chapters[-1].chapter_num
            last_ch_end = found_chapters[-1].end_pos if found_chapters[-1].end_pos else self.book_end_pos
            pos_map[last_ch_num + 1] = last_ch_end
        else:
            pos_map[len(self.chapter_titles) + 1] = self.book_end_pos

        sorted_nums = sorted(pos_map.keys())

        for i in range(len(sorted_nums) - 1):
            prev_ch_num = sorted_nums[i]
            next_ch_num_in_map = sorted_nums[i+1]
            
            if next_ch_num_in_map - prev_ch_num <= 1:
                continue

            search_start = pos_map[prev_ch_num]
            search_end = pos_map[next_ch_num_in_map]
            
            gap_text = self.text[search_start:search_end]
            
            for missing_ch_num in range(prev_ch_num + 1, next_ch_num_in_map):
                if missing_ch_num in found_nums:
                    continue
                if missing_ch_num > len(self.chapter_titles):
                    break
                    
                title = self.chapter_titles[missing_ch_num - 1]
                snippet = self._get_partial_title_snippet(title, num_words=3, min_len=10)

                # Use the 'clean' regex + a 'subsection' regex
                patterns = [
                    rf"(?:^|\n)\s*(##+)\s*(?:Chapter|CHAPTER)\s+{missing_ch_num}(?![0-9.])\b",
                    rf"(?:^|\n)\s*(##+)\s*{missing_ch_num}(?![0-9.])\b",
                    # Add the '6.1' style fix here too
                    rf"(?:^|\n)\s*(##+)\s*{missing_ch_num}\.1\s*[:\.\-]?\s*{re.escape(snippet or '')}"
                ]
                
                if snippet:
                    patterns.append(rf"(?:^|\n)\s*{re.escape(snippet)}[^\n]*\s*(?:\n|$)")
                
                for p in patterns:
                    try:
                        for match in re.finditer(p, gap_text, re.IGNORECASE | re.MULTILINE):
                            match_pos = search_start + match.start()

                            candidate = ChapterBoundary(
                                chapter_num=missing_ch_num,
                                title=title,
                                start_pos=match_pos,
                                confidence=0.8,
                                detection_method="gap_filler"
                            )

                            if self._validate_position(candidate, found_chapters + new_finds):
                                new_finds.append(candidate)
                                found_nums.add(missing_ch_num)
                                break 
                    except re.error:
                        pass
                
                if missing_ch_num in found_nums:
                    break 
        
        return new_finds

    def _find_match(self, pattern: str, idx: int, title: str, confidence: float, 
                      candidates: List[ChapterBoundary], flags: re.RegexFlag = re.RegexFlag(0)) -> bool:
        """Helper to find a regex match and add it to candidates list"""
        try:
            for match in re.finditer(pattern, self.text[:self.book_end_pos], flags | re.MULTILINE):
                candidates.append(ChapterBoundary(
                    chapter_num=idx,
                    title=title,
                    start_pos=match.start(),
                    confidence=confidence
                ))
                return True 
        except re.error:
            pass 
        return False

    def _validate_position(self, candidate: ChapterBoundary, existing: List[ChapterBoundary]) -> bool:
        """Validate that position makes sense."""
        if candidate.start_pos < self.book_start_pos:
            return False

        for existing_chapter in existing:
            if existing_chapter.chapter_num < candidate.chapter_num:
                if candidate.start_pos <= existing_chapter.start_pos:
                    return False
            elif existing_chapter.chapter_num > candidate.chapter_num:
                if candidate.start_pos >= existing_chapter.start_pos:
                    return False
        return True

    def _normalize_text(self, text: str) -> str:
        """Normalize for comparison"""
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity score"""
        norm1 = self._normalize_text(str1)
        norm2 = self._normalize_text(str2)
        return SequenceMatcher(None, norm1, norm2).ratio()

    def _looks_like_heading(self, text: str) -> bool:
        """Check if text looks like it could be a heading"""
        first_line = text.split('\n')[0].strip()
        if not first_line or len(first_line) > 150: return False
        if first_line.startswith('#'): return True
        if first_line.isupper() and len(first_line) < 100: return True
        if re.match(r'^\d+[\.\s\-:]', first_line): return True
        if first_line.istitle() and len(first_line) > 10: return True
        return False

# ============================================================================
# BOOK BOUNDARY DETECTION
# ============================================================================

def _find_front_matter_end(text: str, search_ratio: float = 0.20) -> int:
    """Finds the last occurrence of common front-matter keywords."""
    front_matter_keywords = [
        'contents', 'table of contents', 'preface', 
        'dedication', 'copyright', 'introduction'
    ]
    search_limit = int(len(text) * search_ratio)
    if search_limit <= 0:
        return 0
    
    text_lower_subset = text[:search_limit].lower()
    
    last_pos = 0
    for keyword in front_matter_keywords:
        found_pos = text_lower_subset.rfind(keyword)
        if found_pos > last_pos:
            # Add length of keyword to ensure boundary is AFTER the keyword
            last_pos = found_pos + len(keyword)
    
    return last_pos

def detect_book_boundaries(text: str, first_chapter_title: Optional[str] = None) -> Tuple[int, int]:
    """Find actual content boundaries, excluding front/back matter."""
    start_pos = 0
    
    end_pos = len(text)
    end_patterns = [
        r'(?:^|\n)\s*(?:References|REFERENCES)\s*$',
        r'(?:^|\n)\s*(?:Bibliography|BIBLIOGRAPHY)\s*$',
        r'(?:^|\n)\s*(?:Index|INDEX)\s*$',
        r'(?:^|\n)\s*(?:Appendix|APPENDIX)\s+[A-Z0-9]\b',
    ]

    search_start_for_end = int(len(text) * 0.67)
    
    for pattern in end_patterns:
        try:
            matches = list(re.finditer(pattern, text[search_start_for_end:], re.IGNORECASE | re.MULTILINE))
            if matches:
                first_match_pos = matches[0].start() + search_start_for_end
                end_pos = min(end_pos, first_match_pos)
        except re.error:
            continue

    return start_pos, end_pos

# ============================================================================
# CHUNKING WITH INTELLIGENT GAP HANDLING (RE-INCORPORATED)
# ============================================================================

def split_text_into_chunks(text: str) -> List[str]:
    """Split text into semantic chunks"""
    chunks = []
    current_chunk = []
    current_size = 0
    paragraphs = re.split(r'\n\s*\n', text)

    for para in paragraphs:
        para = para.strip()
        if not para: continue
        para_size = len(para)

        if current_size + para_size > CHUNK_SIZE and current_size >= MIN_CHUNK_SIZE:
            chunks.append('\n\n'.join(current_chunk))
            current_chunk = [para]
            current_size = para_size
        else:
            current_chunk.append(para)
            current_size += para_size + 2 

    if current_chunk:
        chunks.append('\n\n'.join(current_chunk))
    return chunks

def create_chunks_from_boundaries(boundaries: BookBoundaries) -> List[Chunk]:
    """
    Create chunks from detected boundaries with intelligent gap labeling, 
    confidence scores, and position percentages (Stage 2 alignment).
    """
    chunks = []

    try:
        # Use the correct global variable INPUT_LOGIC_DIR
        with open(INPUT_LOGIC_DIR / f"{boundaries.book_name}.mmd", 'r', encoding='utf-8') as f:
            text = f.read()
    except FileNotFoundError:
        print(f"    ✗ ERROR: Could not read file {boundaries.book_name}.mmd to create chunks.")
        return []

    book_length = boundaries.book_end - boundaries.book_start

    if boundaries.chapters:
        sorted_chapters = sorted(boundaries.chapters, key=lambda x: x.start_pos)
        detected_chapter_nums = {ch.chapter_num for ch in sorted_chapters}
        
        # Determine all expected chapters (for position percent and missing chapters)
        yaml_chapter_count = boundaries.detection_stats.get('yaml_chapters', 0)
        all_expected_chapters = set(range(1, yaml_chapter_count + 1))
        missing_chapters = sorted(list(all_expected_chapters - detected_chapter_nums))
        
        current_pos = boundaries.book_start
        
        for i, chapter in enumerate(sorted_chapters):
            
            # 1. Handle gap before this chapter
            if current_pos < chapter.start_pos:
                gap_start = current_pos
                gap_end = chapter.start_pos
                gap_text = text[gap_start:gap_end]
                text_chunks = split_text_into_chunks(gap_text)
                
                # Determine label for this gap
                prev_ch_num = sorted_chapters[i-1].chapter_num if i > 0 else 0
                
                # Find which missing chapters likely fall in this gap
                gap_start_percent = (gap_start - boundaries.book_start) / book_length * 100
                gap_end_percent = (gap_end - boundaries.book_start) / book_length * 100
                likely_missing = []
                
                # Assign missing chapter if its proportional position falls within the gap
                for missing_num in missing_chapters:
                    if yaml_chapter_count == 0:
                        continue 
                    expected_pos_percent = (missing_num / yaml_chapter_count) * 100
                    if gap_start_percent <= expected_pos_percent <= gap_end_percent:
                        likely_missing.append(missing_num)
                
                # Generate gap label
                if likely_missing:
                    missing_str = ','.join(str(n) for n in sorted(likely_missing))
                    chapter_label = f"between-ch{prev_ch_num}-ch{chapter.chapter_num}[likely-ch{missing_str}]"
                    chapter_title = f"Gap: Likely Chapter(s) {missing_str}"
                elif prev_ch_num > 0:
                    chapter_label = f"between-ch{prev_ch_num}-ch{chapter.chapter_num}"
                    chapter_title = f"Gap between Chapter {prev_ch_num} and Chapter {chapter.chapter_num}"
                else:
                    chapter_label = f"pre-ch{chapter.chapter_num}"
                    chapter_title = f"Before Chapter {chapter.chapter_num}"
                
                for chunk_idx, chunk_text in enumerate(text_chunks):
                    char_start_pos = gap_start + sum(len(c) + 2 for c in text_chunks[:chunk_idx]) # Approximate start
                    position_percent = (char_start_pos - boundaries.book_start) / book_length * 100
                    chunk_id = f"{boundaries.book_name}_gap{i}_{chunk_idx}"
                    chunks.append(Chunk(
                        chunk_id=chunk_id,
                        book_name=boundaries.book_name,
                        chapter_number=None, # Explicitly None for gaps
                        chapter_title=chapter_label, # Use the generated label
                        chunk_index_in_chapter=chunk_idx,
                        total_chunks_in_chapter=len(text_chunks),
                        text=chunk_text,
                        char_start=char_start_pos,
                        char_end=gap_end,
                        chunking_method="gap_between_chapters",
                        confidence=0.5, # Default confidence for gaps
                        position_percent=position_percent
                    ))
                
            # 2. Process the detected chapter
            chapter_end = chapter.end_pos or boundaries.book_end
            chapter_text = text[chapter.start_pos:chapter_end]
            text_chunks = split_text_into_chunks(chapter_text)
            
            for chunk_idx, chunk_text in enumerate(text_chunks):
                char_start_pos = chapter.start_pos + sum(len(c) + 2 for c in text_chunks[:chunk_idx])
                position_percent = (char_start_pos - boundaries.book_start) / book_length * 100
                chunk_id = f"{boundaries.book_name}_ch{chapter.chapter_num}_{chunk_idx}"
                chunks.append(Chunk(
                    chunk_id=chunk_id,
                    book_name=boundaries.book_name,
                    chapter_number=chapter.chapter_num,
                    chapter_title=chapter.title,
                    chunk_index_in_chapter=chunk_idx,
                    total_chunks_in_chapter=len(text_chunks),
                    text=chunk_text,
                    char_start=chapter.start_pos,
                    char_end=chapter_end,
                    chunking_method=f"detected_{chapter.detection_method}",
                    confidence=chapter.confidence,
                    position_percent=position_percent
                ))
            
            current_pos = chapter_end
        
        # 3. Handle gap after last chapter
        if current_pos < boundaries.book_end:
            gap_start = current_pos
            gap_end = boundaries.book_end
            gap_text = text[gap_start:gap_end]
            text_chunks = split_text_into_chunks(gap_text)
            last_chapter = sorted_chapters[-1]
            
            # Find remaining missing chapters
            gap_start_percent = (gap_start - boundaries.book_start) / book_length * 100
            likely_missing = [num for num in missing_chapters 
                             if (num / yaml_chapter_count) * 100 > gap_start_percent]
            
            if likely_missing:
                missing_str = ','.join(str(n) for n in sorted(likely_missing))
                chapter_label = f"post-ch{last_chapter.chapter_num}[likely-ch{missing_str}]"
                chapter_title = f"After Chapter {last_chapter.chapter_num}: Likely Chapter(s) {missing_str}"
            else:
                chapter_label = f"post-ch{last_chapter.chapter_num}"
                chapter_title = f"After Chapter {last_chapter.chapter_num} (Back Matter/Unstructured)"
            
            for chunk_idx, chunk_text in enumerate(text_chunks):
                char_start_pos = gap_start + sum(len(c) + 2 for c in text_chunks[:chunk_idx])
                position_percent = (char_start_pos - boundaries.book_start) / book_length * 100
                chunk_id = f"{boundaries.book_name}_endgap_{chunk_idx}"
                chunks.append(Chunk(
                    chunk_id=chunk_id,
                    book_name=boundaries.book_name,
                    chapter_number=None,
                    chapter_title=chapter_label,
                    chunk_index_in_chapter=chunk_idx,
                    total_chunks_in_chapter=len(text_chunks),
                    text=chunk_text,
                    char_start=gap_start,
                    char_end=gap_end,
                    chunking_method="gap_after_chapters",
                    confidence=0.3,
                    position_percent=position_percent
                ))
    else:
        # Fallback: no chapters detected at all
        book_text = text[boundaries.book_start:boundaries.book_end]
        text_chunks = split_text_into_chunks(book_text)
        for chunk_idx, chunk_text in enumerate(text_chunks):
            position_percent = ((boundaries.book_start + (chunk_idx * CHUNK_SIZE)) / len(text)) * 100
            chunk_id = f"{boundaries.book_name}_fallback_{chunk_idx}"
            chunks.append(Chunk(
                chunk_id=chunk_id,
                book_name=boundaries.book_name,
                chapter_number=None,
                chapter_title="no-chapters-detected",
                chunk_index_in_chapter=chunk_idx,
                total_chunks_in_chapter=len(text_chunks),
                text=chunk_text,
                char_start=boundaries.book_start,
                char_end=boundaries.book_end,
                chunking_method="fallback_no_chapters",
                confidence=0.0,
                position_percent=position_percent
            ))
            
    return chunks

# ============================================================================
# MAIN PROCESSING
# ============================================================================

def process_book(book_path: Path, yaml_data: Dict) -> Optional[BookBoundaries]:
    """Process a single book to find all boundaries"""
    # ... (Same logic as provided in your code)
    book_name = book_path.stem
    book_filename = book_path.name
    
    try:
        text = book_path.read_text(encoding='utf-8')
    except Exception as e:
        print(f"\n{'='*80}")
        print(f"📖 FAILED Processing: {book_name}")
        print(f"    ✗ ERROR reading file: {e}")
        print(f"{'='*80}")
        return None

    print(f"\n{'='*80}")
    print(f"📖 Processing: {book_name}")
    print(f"{'='*80}")

    chapter_titles = yaml_data.get(book_filename, [])
    
    first_title = chapter_titles[0] if chapter_titles else None
    book_start, book_end = detect_book_boundaries(text, first_title)
    
    front_matter_boundary = _find_front_matter_end(text)
    
    print(f"    Book boundaries: {book_start} to {book_end}")
    print(f"    Book length: {book_end - book_start:,} characters")
    print(f"    Front matter boundary: {front_matter_boundary}")

    detected_chapters = []
    if chapter_titles:
        print(f"    YAML chapters: {len(chapter_titles)}")
        
        detector = ChapterDetector(
            text, 
            chapter_titles, 
            book_start_pos=book_start,
            book_end_pos=book_end,
            front_matter_boundary=front_matter_boundary
        )
        detected_chapters = detector.detect_all_chapters()
        print(f"    Detected: {len(detected_chapters)}/{len(chapter_titles)} chapters")
    else:
        print(f"    No YAML chapters provided")

    detection_stats = {
        'yaml_chapters': len(chapter_titles),
        'detected_chapters': len(detected_chapters),
        'detection_rate': len(detected_chapters) / len(chapter_titles) if chapter_titles else 0,
        'methods_used': list(set(ch.detection_method for ch in detected_chapters))
    }
    
    boundaries = BookBoundaries(
        book_name=book_name,
        book_start=book_start,
        book_end=book_end,
        chapters=detected_chapters,
        detection_stats=detection_stats
    )
    return boundaries

def main():
    """Main execution"""

    print("=" * 80)
    print("AGGRESSIVE CHAPTER DETECTION FOR OCR'D BOOKS")
    print("=" * 80)

    try:
        with open(YAML_FILE, 'r', encoding='utf-8') as f:
            yaml_data = yaml.safe_load(f)
        if not yaml_data:
             print(f"⚠ Warning: YAML file is empty. {YAML_FILE}")
             yaml_data = {}
        print(f"\n✓ Loaded YAML metadata")
    except FileNotFoundError:
        print(f"✗ Error: YAML file not found at {YAML_FILE}")
        print("Please create this file and add your chapter lists.")
        yaml_data = {}
    except Exception as e:
        print(f"✗ Error loading YAML: {e}")
        yaml_data = {}

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    all_boundaries = []
    all_stats = []
    
    # Fix the undeclared variable by using a global pointer.
    global INPUT_LOGIC_DIR 
    INPUT_LOGIC_DIR = INPUT_DIR

    for book_path in sorted(INPUT_DIR.glob("*.mmd")):
        boundaries = process_book(book_path, yaml_data)
        if boundaries is None:
            continue
            
        all_boundaries.append(boundaries)
        chunks = create_chunks_from_boundaries(boundaries)

        output_file = OUTPUT_DIR / f"{boundaries.book_name}_chunks.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump([asdict(chunk) for chunk in chunks], f, indent=2)

        boundaries_file = OUTPUT_DIR / f"{boundaries.book_name}_boundaries.json"
        with open(boundaries_file, 'w', encoding='utf-8') as f:
            json.dump({
                'book_name': boundaries.book_name,
                'book_start': boundaries.book_start,
                'book_end': boundaries.book_end,
                'chapters': [asdict(ch) for ch in boundaries.chapters],
                'stats': boundaries.detection_stats
            }, f, indent=2)

        all_stats.append({
            'book': boundaries.book_name,
            'chunks_created': len(chunks),
            **boundaries.detection_stats
        })

    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    total_chapters_expected = sum(b.detection_stats['yaml_chapters'] for b in all_boundaries if b)
    total_chapters_found = sum(b.detection_stats['detected_chapters'] for b in all_boundaries if b)

    if total_chapters_expected > 0:
        print(f"\nOverall detection rate: {total_chapters_found}/{total_chapters_expected} "
              f"({100 * total_chapters_found / total_chapters_expected:.1f}%)")
    else:
        print("\nOverall detection rate: 0/0 (No chapters in YAML)")

    print("\nPer-book results:")
    for boundaries in all_boundaries:
        stats = boundaries.detection_stats
        symbol = "→"
        if stats['yaml_chapters'] > 0:
            rate = stats['detected_chapters'] / stats['yaml_chapters']
            if rate == 1.0: symbol = "✓"
            elif rate >= 0.9: symbol = "⚠" # 90%+
            elif rate > 0: symbol = "✗"
            else: symbol = "!" # 0 found
        
        print(f"    {symbol} {boundaries.book_name}: {stats['detected_chapters']}/{stats['yaml_chapters']} chapters")
        if stats['methods_used']:
            print(f"            Methods: {', '.join(sorted(list(stats['methods_used'])))}")

    stats_file = OUTPUT_DIR / "detection_stats.json"
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(all_stats, f, indent=2)

    print(f"\n{'='*80}")
    print(f"✓ Processing complete")
    print(f"✓ Chunks saved to: {OUTPUT_DIR}")
    print(f"✓ Stats saved to: {stats_file}")
    print(f"{'='*80}")

if __name__ == "__main__":
    main()