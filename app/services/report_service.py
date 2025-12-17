import os
from io import BytesIO
from typing import List, Optional
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT

from app.models.db import SwingSession

class ReportService:
    def __init__(self, storage_dir: str = "videos"):
        self.storage_dir = storage_dir
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=16,
            spaceAfter=12,
            textColor=colors.HexColor('#1e40af')  # Blue-800
        ))
        self.styles.add(ParagraphStyle(
            name='MetricName',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.black
        ))
        self.styles.add(ParagraphStyle(
            name='MetricValue',
            parent=self.styles['Normal'],
            fontSize=10,
            alignment=TA_CENTER
        ))
        self.styles.add(ParagraphStyle(
            name='FeedbackText',
            parent=self.styles['Normal'],
            fontSize=10,
            leading=14
        ))
        self.styles.add(ParagraphStyle(
            name='PhaseTitle',
            parent=self.styles['Heading3'],
            fontSize=12,
            spaceAfter=6,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#1f2937')
        ))

    def generate_report(self, session: SwingSession) -> BytesIO:
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=50, leftMargin=50,
            topMargin=50, bottomMargin=50
        )
        
        story = []
        
        # --- HEADER ---
        story.append(Paragraph("Golf Swing Analysis Report", self.styles['Title']))
        story.append(Paragraph(f"Session Date: {session.created_at.strftime('%Y-%m-%d %H:%M')}", self.styles['Normal']))
        story.append(Spacer(1, 20))

        # --- SCORE SUMMARY ---
        self._add_score_summary(story, session)
        story.append(Spacer(1, 20))

        # --- COACH'S FEEDBACK ---
        if session.feedback:
            self._add_feedback_section(story, session)
            story.append(Spacer(1, 20))

        # --- PRIORITY ISSUES ---
        if session.feedback and session.feedback.priority_issues:
            self._add_priority_issues(story, session)
            story.append(PageBreak())

        # --- METRICS ---
        if session.metrics:
            story.append(Paragraph("Swing Metrics", self.styles['SectionHeader']))
            self._add_metrics_table(story, session)
            story.append(PageBreak())

        # --- VISUAL ANALYSIS ---
        story.append(Paragraph("Phase Analysis", self.styles['SectionHeader']))
        self._add_phase_analysis(story, session)

        doc.build(story)
        buffer.seek(0)
        return buffer

    def _add_score_summary(self, story, session):
        score_color = colors.green if session.overall_score >= 80 else colors.orange if session.overall_score >= 60 else colors.red
        
        data = [
            ["Overall Score", f"{session.overall_score}/100"],
            ["Club", session.club_type.title() if session.club_type else "N/A"],
            ["Handedness", session.handedness.title() if session.handedness else "N/A"]
        ]
        
        t = Table(data, colWidths=[2*inch, 2*inch], hAlign='LEFT')
        t.setStyle(TableStyle([
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 12),
            ('TEXTCOLOR', (1,0), (1,0), score_color),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(t)

    def _add_feedback_section(self, story, session):
        story.append(Paragraph("Coach's Summary", self.styles['SectionHeader']))
        story.append(Paragraph(session.feedback.summary, self.styles['FeedbackText']))

    def _add_priority_issues(self, story, session):
        story.append(Paragraph("Priority Issues", self.styles['SectionHeader']))
        for issue in session.feedback.priority_issues:
            # Bullet point style
            p = Paragraph(f"• {issue}", self.styles['FeedbackText'])
            story.append(p)
            story.append(Spacer(1, 4))
            
    def _add_metrics_table(self, story, session):
        metrics = session.metrics
        if not metrics:
            return

        # Helper to get value
        def get_val(attr, fmt="{:.1f}"):
            val = getattr(metrics, attr, None)
            if val is None:
                return "-"
            if isinstance(val, (int, float)):
                 return fmt.format(val)
            return str(val)

        # Categories mapping
        categories = [
            ("Timing & Tempo", [
                ("Tempo Ratio", "tempo_ratio", "{:.2f}"),
                ("Backswing Time", "backswing_duration_ms", lambda x: f"{x/1000:.2f}s"),
                ("Downswing Time", "downswing_duration_ms", lambda x: f"{x/1000:.2f}s"),
            ]),
            ("Rotation", [
                ("Chest Turn (Top)", "chest_turn_top_deg", "{:.1f}°"),
                ("Pelvis Turn (Top)", "pelvis_turn_top_deg", "{:.1f}°"),
                ("X-Factor (Top)", "x_factor_top_deg", "{:.1f}°"),
                ("Shoulder Turn (Top)", "shoulder_turn_top_deg", "{:.1f}°"),
                ("Hip Turn (Top)", "hip_turn_top_deg", "{:.1f}°"),
            ]),
            ("Posture & Balance", [
                ("Spine Angle (Address)", "spine_angle_address_deg", "{:.1f}°"),
                ("Spine Angle (Impact)", "spine_angle_impact_deg", "{:.1f}°"),
                ("Spine Tilt (Address)", "spine_tilt_address_deg", "{:.1f}°"),
                ("Spine Tilt (Impact)", "spine_tilt_impact_deg", "{:.1f}°"),
                ("Finish Balance", "finish_balance", "{:.1f}"),
                ("Early Extension", "early_extension_amount", "{:.2f}"),
            ]),
            ("Arm & Club Structure", [
                ("Lead Arm (Address)", "lead_arm_address_deg", "{:.1f}°"),
                ("Lead Arm (Top)", "lead_arm_top_deg", "{:.1f}°"),
                ("Lead Arm (Impact)", "lead_arm_impact_deg", "{:.1f}°"),
                ("Trail Elbow (Address)", "trail_elbow_address_deg", "{:.1f}°"),
                ("Trail Elbow (Top)", "trail_elbow_top_deg", "{:.1f}°"),
                ("Trail Elbow (Impact)", "trail_elbow_impact_deg", "{:.1f}°"),
                ("Shaft Lean (Impact)", "shaft_lean_impact_deg", "{:.1f}°"),
            ]),
              ("Wrist Angles", [
                ("Lead Flexion (Address)", "lead_wrist_flexion_address_deg", "{:.1f}°"),
                ("Lead Flexion (Top)", "lead_wrist_flexion_top_deg", "{:.1f}°"),
                ("Lead Flexion (Impact)", "lead_wrist_flexion_impact_deg", "{:.1f}°"),
                 ("Lead Hinge (Top)", "lead_wrist_hinge_top_deg", "{:.1f}°"),
            ]),
            ("Head Movement", [
                 ("Head Sway Range", "head_sway_range", "{:.2f}"),
                 ("Head Drop", "head_drop_cm", "{:.1f} cm"),
                 ("Head Rise", "head_rise_cm", "{:.1f} cm"),
                 ("Vertical Move", "head_movement_vertical_cm", "{:.1f} cm"),
                 ("Forward Move", "head_movement_forward_cm", "{:.1f} cm"),
            ]),
            ("Path & Plane", [
                ("Swing Path Index", "swing_path_index", "{:.3f}"),
                 ("Hand Height (Top)", "hand_height_at_top_index", "{:.3f}"),
                 ("Hand Width (Top)", "hand_width_at_top_index", "{:.3f}"),
            ])
        ]

        data = []
        
        # Styles for the table
        table_styles = [
            ('GRID', (0,0), (-1,-1), 1, colors.HexColor('#e5e7eb')),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]
        
        row_idx = 0
        for category_name, items in categories:
            # Add Category Header Row
            data.append([category_name.upper(), ""])
            table_styles.append(('SPAN', (0, row_idx), (1, row_idx)))
            table_styles.append(('BACKGROUND', (0, row_idx), (1, row_idx), colors.HexColor('#1e40af'))) # Blue-800
            table_styles.append(('TEXTCOLOR', (0, row_idx), (1, row_idx), colors.white))
            table_styles.append(('FONTNAME', (0, row_idx), (1, row_idx), 'Helvetica-Bold'))
            table_styles.append(('ALIGN', (0, row_idx), (1, row_idx), 'LEFT'))
            table_styles.append(('LEFTPADDING', (0, row_idx), (1, row_idx), 10))
            row_idx += 1
            
            # Add Metric Rows
            for name, key, format_func in items:
                # Check if metric exists (even if None, we might want to show it as "-")
                # But if the attribute creates an error, skip it.
                if not hasattr(metrics, key):
                     continue
                     
                val = getattr(metrics, key)
                
                # Format value
                val_str = "-"
                if val is not None:
                    if callable(format_func):
                         val_str = format_func(val)
                    else:
                         val_str = format_func.format(val)
                
                data.append([name, val_str])
                
                # Stripe rows
                if row_idx % 2 == 1:
                     table_styles.append(('BACKGROUND', (0, row_idx), (-1, row_idx), colors.HexColor('#f3f4f6'))) # Grey-100
                else:
                     table_styles.append(('BACKGROUND', (0, row_idx), (-1, row_idx), colors.white))
                     
                table_styles.append(('TEXTCOLOR', (0, row_idx), (-1, row_idx), colors.HexColor('#1f2937'))) # Grey-800
                table_styles.append(('LEFT', (0, row_idx), (-1, row_idx), 'LEFT'))
                table_styles.append(('FONTNAME', (0, row_idx), (-1, row_idx), 'Helvetica'))
                
                row_idx += 1

        if not data:
            return

        t = Table(data, colWidths=[3*inch, 2*inch], hAlign='LEFT')
        t.setStyle(TableStyle(table_styles))
        story.append(t)

    def _add_phase_analysis(self, story, session):
        phases = ["address", "top", "impact", "finish"]
        
        # We want a 2x2 grid ideally, but flowable images in ReportLab are easier to handle sequentially or in rows of 2.
        # Let's do rows of 2.
        
        rows = []
        current_row = []
        
        from reportlab.lib.utils import ImageReader

        for phase in phases:
            image_path = os.path.join(self.storage_dir, f"{session.id}_{phase}.jpg")
            
            # Check if file exists
            if not os.path.exists(image_path):
                continue
                
            try:
                # Get image dimensions to preserve aspect ratio
                img_reader = ImageReader(image_path)
                iw, ih = img_reader.getSize()
                aspect = ih / float(iw)
                
                # Limit width to 3 inches, calculate height
                display_width = 3 * inch
                display_height = display_width * aspect
                
                img = Image(image_path, width=display_width, height=display_height)
                img.hAlign = 'CENTER'
            except Exception as e:
                # Fallback if image reading fails
                print(f"Error reading image {image_path}: {e}")
                continue
            
            feedback_text = ""
            if session.feedback and session.feedback.phase_feedback:
                # Retrieve from JSON dict
                fb = session.feedback.phase_feedback
                if isinstance(fb, dict):
                    feedback_text = fb.get(phase, "")
            
            if not feedback_text:
                feedback_text = "No specific feedback available."

            # Create a mini-story for this cell
            cell_content = [
                Paragraph(phase.title(), self.styles['PhaseTitle']),
                img,
                Spacer(1, 6),
                Paragraph(feedback_text, self.styles['FeedbackText'])
            ]
            
            current_row.append(cell_content)
            
            if len(current_row) == 2:
                rows.append(current_row)
                current_row = []
        
        if current_row:
            rows.append(current_row)
            
        # Build the main table
        # ReportLab tables take raw data (strings or Flowables)
        # We need to wrap cell_content in a container calculation or use a nested table for each cell to ensure it stays together?
        # Actually Table cells can contain a list of Flowables.
        
        table_data = []
        for row in rows:
            table_row = []
            for cell_items in row:
                # We can't put a list of flowables directly into a Table cell easily without some adapter.
                # A common wrapper is using a temporary list
                # Easiest way in Platypus is to put [Image, Paragraph] into the cell
                table_row.append(cell_items)
            
            # If row is incomplete, pad it
            while len(table_row) < 2:
                table_row.append("") # Empty cell
            
            table_data.append(table_row)
            
        if not table_data:
            story.append(Paragraph("No images found for phase analysis.", self.styles['Normal']))
            return

        t = Table(table_data, colWidths=[3.5*inch, 3.5*inch])
        t.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING', (0,0), (-1,-1), 6),
            ('RIGHTPADDING', (0,0), (-1,-1), 6),
            ('TOPPADDING', (0,0), (-1,-1), 12),
        ]))
        story.append(t)
