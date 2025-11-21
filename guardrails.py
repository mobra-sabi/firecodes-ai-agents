#!/usr/bin/env python3
"""
Guardrails - Securitate & Conformitate
Implementează guardrails pentru rate limiting, auth, audit logs, PII scrubbing
"""

import asyncio
import time
import json
import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from collections import defaultdict, deque
import hashlib
import secrets
from enum import Enum

logger = logging.getLogger(__name__)

class SecurityLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class SecurityEvent:
    """Eveniment de securitate"""
    event_type: str
    level: SecurityLevel
    message: str
    user_id: Optional[str]
    agent_id: Optional[str]
    ip_address: Optional[str]
    timestamp: datetime
    metadata: Dict = None

@dataclass
class RateLimitInfo:
    """Informații despre rate limiting"""
    requests_count: int
    window_start: datetime
    limit: int
    window_duration: int  # secunde

class Guardrails:
    """Sistem de guardrails pentru securitate și conformitate"""
    
    def __init__(self, config: Dict):
        self.config = config
        
        # Rate limiting
        self.rate_limits = defaultdict(lambda: deque())
        self.rate_limit_config = {
            'requests_per_minute': config.get('requests_per_minute', 60),
            'burst_limit': config.get('burst_limit', 10),
            'window_duration': 60  # secunde
        }
        
        # Audit logging
        self.audit_log = []
        self.max_audit_log_size = config.get('max_audit_log_size', 10000)
        
        # PII detection patterns
        self.pii_patterns = {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'(\+40|0)[0-9]{9}',
            'cnp': r'[0-9]{13}',
            'iban': r'RO[0-9]{2}[A-Z]{4}[0-9]{16}',
            'credit_card': r'[0-9]{4}[-\s]?[0-9]{4}[-\s]?[0-9]{4}[-\s]?[0-9]{4}',
            'address': r'str\.?\s+[A-Za-z\s]+,\s*nr\.?\s*[0-9]+',
            'name': r'(?:domnul|doamna|dl\.|dna\.)\s+[A-Z][a-z]+\s+[A-Z][a-z]+'
        }
        
        # Blocked patterns
        self.blocked_patterns = [
            r'password\s*[:=]\s*\w+',
            r'token\s*[:=]\s*\w+',
            r'api[_-]?key\s*[:=]\s*\w+',
            r'secret\s*[:=]\s*\w+',
            r'<script.*?>.*?</script>',
            r'javascript:',
            r'data:text/html',
            r'vbscript:',
            r'onload\s*=',
            r'onerror\s*='
        ]
        
        # Confidence thresholds
        self.confidence_thresholds = {
            'low': 0.3,
            'medium': 0.5,
            'high': 0.7,
            'critical': 0.9
        }
        
        # Session management
        self.active_sessions = {}
        self.session_timeout = config.get('session_timeout', 3600)  # 1 oră
        
        # API keys (pentru autentificare)
        self.api_keys = set(config.get('valid_api_keys', []))
        
        # Error tracking
        self.error_counts = defaultdict(int)
        self.max_errors_per_minute = config.get('max_errors_per_minute', 10)
    
    async def check_rate_limit(self, user_id: str, ip_address: str) -> Tuple[bool, str]:
        """
        Verifică rate limiting pentru un utilizator
        """
        current_time = datetime.now(timezone.utc)
        window_start = current_time - timedelta(seconds=self.rate_limit_config['window_duration'])
        
        # Curăță request-urile vechi
        user_key = f"{user_id}:{ip_address}"
        while (self.rate_limits[user_key] and 
               self.rate_limits[user_key][0] < window_start):
            self.rate_limits[user_key].popleft()
        
        # Verifică limita
        current_requests = len(self.rate_limits[user_key])
        
        if current_requests >= self.rate_limit_config['requests_per_minute']:
            await self._log_security_event(
                SecurityEvent(
                    event_type="rate_limit_exceeded",
                    level=SecurityLevel.MEDIUM,
                    message=f"Rate limit exceeded for user {user_id}",
                    user_id=user_id,
                    agent_id=None,
                    ip_address=ip_address,
                    timestamp=current_time,
                    metadata={'requests_count': current_requests}
                )
            )
            return False, "Rate limit exceeded. Please try again later."
        
        # Adaugă request-ul curent
        self.rate_limits[user_key].append(current_time)
        
        return True, "OK"
    
    async def check_authentication(self, api_key: Optional[str], session_id: Optional[str]) -> Tuple[bool, str]:
        """
        Verifică autentificarea
        """
        # Verifică API key
        if api_key and api_key in self.api_keys:
            return True, "API key valid"
        
        # Verifică session
        if session_id and session_id in self.active_sessions:
            session_data = self.active_sessions[session_id]
            if session_data['expires_at'] > datetime.now(timezone.utc):
                return True, "Session valid"
            else:
                # Session expirat
                del self.active_sessions[session_id]
        
        await self._log_security_event(
            SecurityEvent(
                event_type="authentication_failed",
                level=SecurityLevel.MEDIUM,
                message="Authentication failed",
                user_id=None,
                agent_id=None,
                ip_address=None,
                timestamp=datetime.now(timezone.utc),
                metadata={'api_key_provided': bool(api_key), 'session_id_provided': bool(session_id)}
            )
        )
        
        return False, "Authentication required"
    
    async def scrub_pii(self, text: str) -> Tuple[str, List[str]]:
        """
        Detectează și elimină PII din text
        """
        detected_pii = []
        scrubbed_text = text
        
        for pii_type, pattern in self.pii_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                detected_pii.extend([(pii_type, match) for match in matches])
                
                # Înlocuiește cu placeholder
                if pii_type == 'email':
                    scrubbed_text = re.sub(pattern, '[EMAIL_REDACTED]', scrubbed_text, flags=re.IGNORECASE)
                elif pii_type == 'phone':
                    scrubbed_text = re.sub(pattern, '[PHONE_REDACTED]', scrubbed_text, flags=re.IGNORECASE)
                elif pii_type == 'cnp':
                    scrubbed_text = re.sub(pattern, '[CNP_REDACTED]', scrubbed_text, flags=re.IGNORECASE)
                elif pii_type == 'iban':
                    scrubbed_text = re.sub(pattern, '[IBAN_REDACTED]', scrubbed_text, flags=re.IGNORECASE)
                elif pii_type == 'credit_card':
                    scrubbed_text = re.sub(pattern, '[CARD_REDACTED]', scrubbed_text, flags=re.IGNORECASE)
                elif pii_type == 'address':
                    scrubbed_text = re.sub(pattern, '[ADDRESS_REDACTED]', scrubbed_text, flags=re.IGNORECASE)
                elif pii_type == 'name':
                    scrubbed_text = re.sub(pattern, '[NAME_REDACTED]', scrubbed_text, flags=re.IGNORECASE)
        
        if detected_pii:
            await self._log_security_event(
                SecurityEvent(
                    event_type="pii_detected",
                    level=SecurityLevel.HIGH,
                    message=f"PII detected and scrubbed: {len(detected_pii)} items",
                    user_id=None,
                    agent_id=None,
                    ip_address=None,
                    timestamp=datetime.now(timezone.utc),
                    metadata={'pii_types': [pii[0] for pii in detected_pii]}
                )
            )
        
        return scrubbed_text, detected_pii
    
    async def check_blocked_content(self, text: str) -> Tuple[bool, List[str]]:
        """
        Verifică dacă conținutul conține pattern-uri blocate
        """
        blocked_found = []
        
        for pattern in self.blocked_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                blocked_found.extend(matches)
        
        if blocked_found:
            await self._log_security_event(
                SecurityEvent(
                    event_type="blocked_content_detected",
                    level=SecurityLevel.HIGH,
                    message=f"Blocked content detected: {len(blocked_found)} patterns",
                    user_id=None,
                    agent_id=None,
                    ip_address=None,
                    timestamp=datetime.now(timezone.utc),
                    metadata={'blocked_patterns': blocked_found}
                )
            )
        
        return len(blocked_found) == 0, blocked_found
    
    async def validate_confidence(self, confidence: float, response_type: str = "answer") -> Tuple[bool, str]:
        """
        Validează nivelul de încredere al răspunsului
        """
        threshold = self.confidence_thresholds.get('medium', 0.5)
        
        if confidence < threshold:
            await self._log_security_event(
                SecurityEvent(
                    event_type="low_confidence_response",
                    level=SecurityLevel.MEDIUM,
                    message=f"Low confidence response: {confidence:.2f}",
                    user_id=None,
                    agent_id=None,
                    ip_address=None,
                    timestamp=datetime.now(timezone.utc),
                    metadata={'confidence': confidence, 'response_type': response_type}
                )
            )
            return False, f"Response confidence too low: {confidence:.2f}"
        
        return True, "Confidence acceptable"
    
    async def check_tool_usage(self, tool_calls: List[Dict], max_steps: int = 3) -> Tuple[bool, str]:
        """
        Verifică utilizarea tool-urilor
        """
        if len(tool_calls) > max_steps:
            await self._log_security_event(
                SecurityEvent(
                    event_type="excessive_tool_usage",
                    level=SecurityLevel.MEDIUM,
                    message=f"Too many tool calls: {len(tool_calls)}",
                    user_id=None,
                    agent_id=None,
                    ip_address=None,
                    timestamp=datetime.now(timezone.utc),
                    metadata={'tool_calls_count': len(tool_calls), 'max_allowed': max_steps}
                )
            )
            return False, f"Too many tool calls: {len(tool_calls)} > {max_steps}"
        
        # Verifică tool-urile permise
        allowed_tools = {'search_index', 'fetch_url', 'calculate', 'get_agent_info', 'search_conversations'}
        
        for tool_call in tool_calls:
            tool_name = tool_call.get('tool')
            if tool_name not in allowed_tools:
                await self._log_security_event(
                    SecurityEvent(
                        event_type="unauthorized_tool",
                        level=SecurityLevel.HIGH,
                        message=f"Unauthorized tool: {tool_name}",
                        user_id=None,
                        agent_id=None,
                        ip_address=None,
                        timestamp=datetime.now(timezone.utc),
                        metadata={'tool_name': tool_name, 'allowed_tools': list(allowed_tools)}
                    )
                )
                return False, f"Unauthorized tool: {tool_name}"
        
        return True, "Tool usage valid"
    
    async def check_error_rate(self, user_id: str) -> Tuple[bool, str]:
        """
        Verifică rata de erori pentru un utilizator
        """
        current_time = datetime.now(timezone.utc)
        minute_ago = current_time - timedelta(minutes=1)
        
        # Curăță erorile vechi
        user_errors = self.error_counts.get(user_id, [])
        user_errors = [error_time for error_time in user_errors if error_time > minute_ago]
        self.error_counts[user_id] = user_errors
        
        if len(user_errors) >= self.max_errors_per_minute:
            await self._log_security_event(
                SecurityEvent(
                    event_type="high_error_rate",
                    level=SecurityLevel.HIGH,
                    message=f"High error rate for user {user_id}",
                    user_id=user_id,
                    agent_id=None,
                    ip_address=None,
                    timestamp=current_time,
                    metadata={'error_count': len(user_errors), 'max_allowed': self.max_errors_per_minute}
                )
            )
            return False, f"Too many errors: {len(user_errors)} in the last minute"
        
        return True, "Error rate acceptable"
    
    async def create_session(self, user_id: str, ip_address: str) -> str:
        """
        Creează o sesiune nouă
        """
        session_id = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=self.session_timeout)
        
        self.active_sessions[session_id] = {
            'user_id': user_id,
            'ip_address': ip_address,
            'created_at': datetime.now(timezone.utc),
            'expires_at': expires_at,
            'last_activity': datetime.now(timezone.utc)
        }
        
        await self._log_security_event(
            SecurityEvent(
                event_type="session_created",
                level=SecurityLevel.LOW,
                message=f"Session created for user {user_id}",
                user_id=user_id,
                agent_id=None,
                ip_address=ip_address,
                timestamp=datetime.now(timezone.utc),
                metadata={'session_id': session_id}
            )
        )
        
        return session_id
    
    async def update_session_activity(self, session_id: str):
        """
        Actualizează activitatea sesiunii
        """
        if session_id in self.active_sessions:
            self.active_sessions[session_id]['last_activity'] = datetime.now(timezone.utc)
    
    async def cleanup_expired_sessions(self):
        """
        Curăță sesiunile expirate
        """
        current_time = datetime.now(timezone.utc)
        expired_sessions = []
        
        for session_id, session_data in self.active_sessions.items():
            if session_data['expires_at'] < current_time:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self.active_sessions[session_id]
        
        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
    
    async def log_error(self, user_id: str, error: str, context: Dict = None):
        """
        Loghează o eroare pentru un utilizator
        """
        current_time = datetime.now(timezone.utc)
        
        if user_id not in self.error_counts:
            self.error_counts[user_id] = []
        
        self.error_counts[user_id].append(current_time)
        
        await self._log_security_event(
            SecurityEvent(
                event_type="error_occurred",
                level=SecurityLevel.MEDIUM,
                message=f"Error for user {user_id}: {error}",
                user_id=user_id,
                agent_id=None,
                ip_address=None,
                timestamp=current_time,
                metadata={'error': error, 'context': context or {}}
            )
        )
    
    async def _log_security_event(self, event: SecurityEvent):
        """
        Loghează un eveniment de securitate
        """
        # Adaugă la audit log
        self.audit_log.append({
            'event_type': event.event_type,
            'level': event.level.value,
            'message': event.message,
            'user_id': event.user_id,
            'agent_id': event.agent_id,
            'ip_address': event.ip_address,
            'timestamp': event.timestamp.isoformat(),
            'metadata': event.metadata or {}
        })
        
        # Limitează dimensiunea audit log-ului
        if len(self.audit_log) > self.max_audit_log_size:
            self.audit_log = self.audit_log[-self.max_audit_log_size:]
        
        # Log în sistem
        log_level = {
            SecurityLevel.LOW: logging.INFO,
            SecurityLevel.MEDIUM: logging.WARNING,
            SecurityLevel.HIGH: logging.ERROR,
            SecurityLevel.CRITICAL: logging.CRITICAL
        }.get(event.level, logging.INFO)
        
        logger.log(log_level, f"Security event: {event.event_type} - {event.message}")
    
    async def get_audit_log(self, limit: int = 100, level: Optional[SecurityLevel] = None) -> List[Dict]:
        """
        Obține audit log-ul
        """
        log_entries = self.audit_log[-limit:] if limit else self.audit_log
        
        if level:
            log_entries = [entry for entry in log_entries if entry['level'] == level.value]
        
        return log_entries
    
    async def get_security_stats(self) -> Dict:
        """
        Obține statistici de securitate
        """
        current_time = datetime.now(timezone.utc)
        last_hour = current_time - timedelta(hours=1)
        
        # Numără evenimentele din ultima oră
        recent_events = [event for event in self.audit_log 
                        if datetime.fromisoformat(event['timestamp']) > last_hour]
        
        event_counts = defaultdict(int)
        for event in recent_events:
            event_counts[event['event_type']] += 1
        
        return {
            'total_events_last_hour': len(recent_events),
            'event_types': dict(event_counts),
            'active_sessions': len(self.active_sessions),
            'rate_limited_users': len(self.rate_limits),
            'total_audit_entries': len(self.audit_log),
            'last_updated': current_time.isoformat()
        }

# Funcție helper pentru a rula guardrails
async def run_guardrails_check(
    user_id: str,
    ip_address: str,
    text: str,
    confidence: float,
    tool_calls: List[Dict],
    config: Dict = None
) -> Tuple[bool, str, Dict]:
    """
    Funcție helper pentru a rula toate verificările de guardrails
    """
    if config is None:
        config = {
            'requests_per_minute': 60,
            'burst_limit': 10,
            'session_timeout': 3600,
            'max_errors_per_minute': 10,
            'max_audit_log_size': 10000,
            'valid_api_keys': []
        }
    
    guardrails = Guardrails(config)
    
    # Verificări de securitate
    checks = []
    
    # 1. Rate limiting
    rate_ok, rate_msg = await guardrails.check_rate_limit(user_id, ip_address)
    checks.append(('rate_limit', rate_ok, rate_msg))
    
    # 2. PII scrubbing
    scrubbed_text, detected_pii = await guardrails.scrub_pii(text)
    checks.append(('pii_scrubbing', True, f"Detected {len(detected_pii)} PII items"))
    
    # 3. Blocked content
    content_ok, blocked_patterns = await guardrails.check_blocked_content(text)
    checks.append(('blocked_content', content_ok, f"Found {len(blocked_patterns)} blocked patterns"))
    
    # 4. Confidence validation
    confidence_ok, confidence_msg = await guardrails.validate_confidence(confidence)
    checks.append(('confidence', confidence_ok, confidence_msg))
    
    # 5. Tool usage
    tool_ok, tool_msg = await guardrails.check_tool_usage(tool_calls)
    checks.append(('tool_usage', tool_ok, tool_msg))
    
    # 6. Error rate
    error_ok, error_msg = await guardrails.check_error_rate(user_id)
    checks.append(('error_rate', error_ok, error_msg))
    
    # Rezultatul final
    all_checks_passed = all(check[1] for check in checks)
    
    result = {
        'all_checks_passed': all_checks_passed,
        'checks': checks,
        'scrubbed_text': scrubbed_text,
        'detected_pii': detected_pii,
        'blocked_patterns': blocked_patterns
    }
    
    if all_checks_passed:
        return True, "All security checks passed", result
    else:
        failed_checks = [check for check in checks if not check[1]]
        return False, f"Security checks failed: {[check[0] for check in failed_checks]}", result

if __name__ == "__main__":
    # Test
    import asyncio
    
    async def test():
        result = await run_guardrails_check(
            user_id="test_user",
            ip_address="127.0.0.1",
            text="My email is test@example.com and my phone is +40712345678",
            confidence=0.8,
            tool_calls=[{'tool': 'search_index', 'args': {'query': 'test'}}]
        )
        print(f"Guardrails result: {result[0]}")
        print(f"Message: {result[1]}")
        print(f"Details: {result[2]}")
    
    asyncio.run(test())



