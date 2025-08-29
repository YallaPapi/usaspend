"""
Advanced deduplication engine for funding data.
Provides identifier-based and heuristic company matching.
"""

import re
import sqlite3
from collections import defaultdict
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from datetime import datetime, date


@dataclass
class CompanyMatch:
    """Represents a potential duplicate company match."""
    company_id: int
    name: str
    country: Optional[str]
    domain: Optional[str]
    confidence: float
    match_type: str  # 'identifier_exact', 'name_similarity', 'domain_match'
    identifiers: Dict[str, str]


class DeduplicationEngine:
    """Engine for detecting and merging duplicate company records."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self._common_words = self._load_common_words()

    def _load_common_words(self) -> Set[str]:
        """Load common words to ignore in company name matching."""
        return {
            'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
            'a', 'an', 'as', 'if', 'it', 'is', 'was', 'be', 'been', 'being', 'have', 'has',
            'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might',
            'must', 'can', 'corp', 'corporation', 'inc', 'incorporated', 'llc', 'ltd',
            'limited', 'co', 'company', 'group', 'holdings', 'enterprises', 'solutions',
            'systems', 'technologies', 'international', 'global', 'usa', 'us', 'america'
        }

    def find_duplicate_candidates(self, company_name: str, country: Optional[str] = None,
                                identifiers: Optional[Dict[str, str]] = None) -> List[CompanyMatch]:
        """
        Find potential duplicate companies based on name, country, and identifiers.

        Returns list of CompanyMatch objects ordered by confidence (highest first).
        """
        candidates = []

        # First, try exact identifier matches (highest confidence)
        if identifiers:
            identifier_matches = self._find_by_identifiers(identifiers)
            for match in identifier_matches:
                candidates.append(CompanyMatch(
                    company_id=match['id'],
                    name=match['name'],
                    country=match['country'],
                    domain=match['domain'],
                    confidence=1.0,  # Exact identifier match = 100% confidence
                    match_type='identifier_exact',
                    identifiers=match['identifiers']
                ))

            # If we found exact identifier matches, return them
            if candidates:
                return candidates

        # No exact identifier matches, try name-based matching
        name_candidates = self._find_by_name_similarity(company_name, country)
        candidates.extend(name_candidates)

        # Sort by confidence (highest first)
        candidates.sort(key=lambda x: x.confidence, reverse=True)

        # Return top candidates (limit to prevent too many options)
        return candidates[:10]

    def _find_by_identifiers(self, identifiers: Dict[str, str]) -> List[Dict]:
        """Find companies with exact identifier matches."""
        matches = []

        # Check each identifier type
        id_types = ['uei', 'duns', 'cik']

        for id_type in id_types:
            if id_type in identifiers and identifiers[id_type]:
                value = identifiers[id_type]
                matches.extend(self._query_identifier_matches(id_type, value))

        return matches

    def _query_identifier_matches(self, id_type: str, value: str) -> List[Dict]:
        """Query database for companies with matching identifiers."""
        # In current schema, identifiers are not stored separately
        # This would need database schema enhancement for production
        # For now, return empty list
        return []

    def _find_by_name_similarity(self, company_name: str, country: Optional[str]) -> List[CompanyMatch]:
        """Find companies with similar names using heuristic matching."""
        candidates = []

        # Get existing companies from database
        existing_companies = self._get_existing_companies(country)

        for company in existing_companies:
            similarity = self._calculate_name_similarity(company_name, company['name'])

            # Only consider substantial matches
            if similarity >= 0.6:  # 60% similarity threshold
                match_type = 'name_similarity'
                confidence = similarity

                # Boost confidence for exact domain matches
                if self._normalized_domain(company_name) == self._normalized_domain(company['name']):
                    confidence = min(0.95, confidence + 0.2)
                    match_type = 'name_similarity_domain'

                candidates.append(CompanyMatch(
                    company_id=company['id'],
                    name=company['name'],
                    country=company['country'],
                    domain=company['domain'],
                    confidence=confidence,
                    match_type=match_type,
                    identifiers={}
                ))

        return candidates

    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity score between two company names."""
        if not name1 or not name2:
            return 0.0

        # Normalize names for comparison
        norm1 = self._normalize_company_name(name1)
        norm2 = self._normalize_company_name(name2)

        # Exact match after normalization
        if norm1 == norm2:
            return 1.0

        # Use sequence matcher for string similarity
        similarity = SequenceMatcher(None, norm1, norm2).ratio()

        # Boost similarity for acronym matches
        if self._is_acronym_match(norm1, norm2):
            similarity = min(1.0, similarity + 0.3)

        # Penalize very short names
        if len(norm1) <= 3 or len(norm2) <= 3:
            similarity *= 0.7

        return min(1.0, similarity)

    def _normalize_company_name(self, name: str) -> str:
        """Normalize company name for comparison."""
        if not name:
            return ""

        # Convert to lowercase
        normalized = name.lower()

        # Remove common punctuation and special characters
        normalized = re.sub(r'[^\w\s]', ' ', normalized)

        # Remove extra whitespace
        normalized = ' '.join(normalized.split())

        # Remove common business suffix variations
        suffixes = [
            r'\bcorp\.?\b', r'\bcorporation\b', r'\bincorporated\b', r'\binc\.?\b',
            r'\bllc\.?\b', r'\blimited\b', r'\bltd\.?\b', r'\bco\.?\b', r'\bcompany\b'
        ]
        for suffix in suffixes:
            normalized = re.sub(suffix, '', normalized)

        # Remove common words
        words = [w for w in normalized.split() if w not in self._common_words]
        normalized = ' '.join(words)

        return normalized.strip()

    def _normalized_domain(self, company_name: str) -> Optional[str]:
        """Extract normalized domain-like string from company name."""
        if not company_name:
            return None

        # Extract potential domain words (remove spaces, keep alphanumeric)
        normalized = re.sub(r'[^a-zA-Z0-9]', '', company_name.lower())
        return normalized if len(normalized) > 3 else None

    def _is_acronym_match(self, name1: str, name2: str) -> bool:
        """Check if one name is an acronym of the other."""
        def get_acronym(name: str) -> str:
            words = name.split()
            if len(words) <= 1:
                return ""
            return ''.join(word[0] for word in words).upper()

        acronym1 = get_acronym(name1)
        acronym2 = get_acronym(name2)

        # Check if acronyms match
        if len(acronym1) >= 3 and acronym1 == acronym2:
            return True

        # Check if one is acronym of the other
        return (acronym1 and acronym1 == name2.replace(' ', '').upper()) or \
               (acronym2 and acronym2 == name1.replace(' ', '').upper())

    def _get_existing_companies(self, country: Optional[str] = None) -> List[Dict]:
        """Get existing companies from database, optionally filtered by country."""
        query = """
            SELECT id, name, country, domain,
                   COALESCE(first_seen, '') as first_seen,
                   COALESCE(last_seen, '') as last_seen
            FROM companies
        """
        params = []

        if country:
            query += " WHERE country = ?"
            params.append(country)

        query += " ORDER BY last_seen DESC"

        cur = self.conn.cursor()
        cur.execute(query, params)
        return [dict(row) for row in cur.fetchall()]

    def merge_duplicate_companies(self, keep_id: int, merge_ids: List[int]) -> bool:
        """
        Merge duplicate company records.
        Updates funding events to point to the kept company and deletes duplicates.
        """
        try:
            cur = self.conn.cursor()

            # Start transaction
            cur.execute("BEGIN")

            # Update funding events to point to kept company
            for merge_id in merge_ids:
                cur.execute(
                    "UPDATE funding_events SET company_id = ? WHERE company_id = ?",
                    (keep_id, merge_id)
                )

            # Update first_seen/last_seen dates if necessary
            cur.execute("""
                UPDATE companies SET
                    first_seen = MIN(first_seen, (
                        SELECT first_seen FROM companies WHERE id = ?
                    )),
                    last_seen = MAX(last_seen, (
                        SELECT last_seen FROM companies WHERE id = ?
                    ))
                WHERE id = ?
            """, (keep_id, keep_id, keep_id))

            # Delete duplicate companies
            placeholders = ','.join('?' * len(merge_ids))
            cur.execute(f"DELETE FROM companies WHERE id IN ({placeholders})", merge_ids)

            # Commit transaction
            self.conn.commit()

            print(f"Merged {len(merge_ids)} duplicate(s) into company {keep_id}")
            return True

        except Exception as e:
            self.conn.rollback()
            print(f"Failed to merge companies: {e}")
            return False

    def find_duplicates_across_dataset(self, min_confidence: float = 0.8) -> List[Tuple[int, List[int]]]:
        """
        Scan entire dataset for duplicates and return merge suggestions.

        Returns: List of (keep_id, [merge_ids]) tuples
        """
        duplicates = []


        return duplicates

    def preview_merge_impact(self, keep_id: int, merge_ids: List[int]) -> Dict:
        """
        Preview the impact of merging companies without actually merging.
        """
        cur = self.conn.cursor()

        # Count events for each company
        event_counts = {}
        companies_info = {}

        all_ids = [keep_id] + merge_ids

        for company_id in all_ids:
            cur.execute("""
                SELECT
                    c.name, c.country, c.domain, c.first_seen, c.last_seen,
                    COUNT(fe.id) as event_count
                FROM companies c
                LEFT JOIN funding_events fe ON fe.company_id = c.id
                WHERE c.id = ?
                GROUP BY c.id
            """, (company_id,))

            row = cur.fetchone()
            if row:
                companies_info[company_id] = dict(row)
                event_counts[company_id] = row['event_count']

        total_events = sum(event_counts.values())

        return {
            'keep_company': companies_info.get(keep_id),
            'merge_companies': {cid: companies_info.get(cid) for cid in merge_ids},
            'total_events_after_merge': total_events - sum(event_counts.get(cid, 0) for cid in merge_ids if cid != keep_id),
            'events_to_transfer': sum(event_counts.get(cid, 0) for cid in merge_ids)
        }