"""
review_packets/Code_Packets/ui_components_design_primitives.py
Parikshak Engineering Review Runtime — UI Components & Design Primitives
Standard: Governed Operational System (Gov-OS) Core Compliance

Provides high-density cognition primitives for:
1. 1-Minute Cognition Reviewer Surface
2. Zero-Context-Switch Niyantran Handover Card
3. Responsive Grid Layouts (Desktop / Tablet / Mobile)
"""

from typing import Dict, Any, List


class UIDesignTokens:
    PALETTE = {
        "surface_bg": "#0B0F19",
        "surface_card": "#111827",
        "border_subtle": "#1F2937",
        "accent_primary": "#3B82F6",
        "accent_success": "#10B981",
        "accent_danger": "#EF4444",
        "accent_warning": "#F59E0B",
        "text_primary": "#F9FAFB",
        "text_secondary": "#9CA3AF"
    }
    TYPOGRAPHY = {
        "font_family_mono": "'JetBrains Mono', 'Fira Code', monospace",
        "font_family_sans": "Inter, system-ui, sans-serif",
        "header_1": "font-size: 1.5rem; font-weight: 700; letter-spacing: -0.025em;",
        "metric_value": "font-size: 2.25rem; font-weight: 800; font-family: mono;",
        "badge_text": "font-size: 0.75rem; font-weight: 600; text-transform: uppercase;"
    }


class HighDensityCognitionCard:
    @staticmethod
    def render_verdict_card(verdict: str, score: float, canonical_hash: str) -> Dict[str, Any]:
        return {
            "component": "HighDensityCognitionCard",
            "verdict": verdict,
            "verdict_color": UIDesignTokens.PALETTE["accent_success"] if verdict == "PASS" else UIDesignTokens.PALETTE["accent_danger"],
            "composite_score": score,
            "sha256_digest": canonical_hash,
            "cognition_sla_seconds": 60,
            "rendered_view": f"[{verdict}] Score: {score}/100 | SHA-256: {canonical_hash[:16]}...{canonical_hash[-8:]}"
        }


class ZeroContextSwitchNiyantranCard:
    @staticmethod
    def render_assignment_action(assigned_task_id: str, candidate_name: str, duration: str) -> Dict[str, Any]:
        return {
            "component": "ZeroContextSwitchNiyantranCard",
            "assigned_task_id": assigned_task_id,
            "candidate_name": candidate_name,
            "duration": duration,
            "action_button": "Approve & Auto-Assign to Niyantran",
            "audit_ledger_target": "Gov-OS Ledger",
            "status": "READY_FOR_SINGLE_CLICK_DISPATCH"
        }
