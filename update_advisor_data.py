#!/usr/bin/env python3
"""
Update advisor bios and focus areas with historically accurate information.
"""

import sqlite3
import json
import sys

DB_PATH = "/Users/shaydu/dev/mondrian-macos/mondrian.db"

# Comprehensive advisor data with bios and focus areas
ADVISOR_DATA = {
    "ansel": {
        "bio": "Adams is the most iconic landscape photographer of the 20th century, best known for his dramatic black-and-white images of the American West, especially Yosemite. He co-developed the Zone System, which revolutionized photographic exposure and printing, and used photography as a powerful tool for environmental conservation.",
        "focus_areas": [
            {"title": "Zone System Precision", "description": "Evaluates tonal range and exposure mastery"},
            {"title": "Environmental Consciousness", "description": "Assesses connection to landscape preservation"},
            {"title": "Dramatic Composition", "description": "Focuses on powerful visual impact and scale"}
        ]
    },
    "watkins": {
        "bio": "Watkins was a pioneer of large-format landscape photography in the 19th century, producing monumental images of Yosemite and the American frontier. His photographs were instrumental in convincing Congress to protect Yosemite, helping lay the groundwork for the U.S. National Park system.",
        "focus_areas": [
            {"title": "Monumental Scale", "description": "Evaluates sense of grandeur and expansive vision"},
            {"title": "Conservation Impact", "description": "Assesses ability to inspire preservation"},
            {"title": "Pioneering Technique", "description": "Focuses on large-format precision and clarity"}
        ]
    },
    "weston": {
        "bio": "Though often associated with still lifes and nudes, Weston's landscapes—especially of the California coast and deserts—are foundational to modernist photography. His work emphasized clarity, form, and tonal precision, influencing generations of photographers to see landscapes as abstract compositions as well as places.",
        "focus_areas": [
            {"title": "Modernist Clarity", "description": "Evaluates sharp focus and formal precision"},
            {"title": "Abstract Vision", "description": "Assesses ability to see beyond literal representation"},
            {"title": "Form and Structure", "description": "Focuses on composition as pure visual poetry"}
        ]
    },
    "cunningham": {
        "bio": "Cunningham was a key member of Group f/64 alongside Ansel Adams and Edward Weston. While celebrated for botanical studies and portraits, her landscapes and nature photographs helped define a sharp-focus, modernist approach that treated the natural world with intimacy and rigor.",
        "focus_areas": [
            {"title": "Botanical Intimacy", "description": "Evaluates close observation of natural detail"},
            {"title": "Sharp-Focus Clarity", "description": "Assesses precision and technical mastery"},
            {"title": "Emotional Resonance", "description": "Focuses on conveying feeling through form"}
        ]
    },
    "gilpin": {
        "bio": "Gilpin is best known for her lyrical photographs of the American Southwest, particularly Navajo lands and communities. Her landscapes combine formal elegance with deep cultural respect, expanding the emotional and ethical scope of landscape photography beyond pure wilderness imagery.",
        "focus_areas": [
            {"title": "Cultural Reverence", "description": "Assesses respect and dignity in representation"},
            {"title": "Southwestern Lyricism", "description": "Evaluates emotional connection to place"},
            {"title": "Formal Elegance", "description": "Focuses on compositional sophistication"}
        ]
    },
    "okeefe": {
        "bio": "O'Keeffe is America's most influential modernist painter, famous for her close-up studies of flowers, skulls, and New Mexico landscapes. She developed a deeply personal visual language that challenged conventions of representation, emphasizing subjective experience and emotional authenticity over literal depiction. Her work bridged American modernism and explored themes of sensuality, spirituality, and the American landscape.",
        "focus_areas": [
            {"title": "Organic Abstraction", "description": "Evaluates transformation of nature into pure form"},
            {"title": "Sensual Color", "description": "Assesses emotional use of vibrant, layered hues"},
            {"title": "Intimate Scale", "description": "Focuses on magnification and personal perspective"}
        ]
    },
    "mondrian": {
        "bio": "Mondrian was a Dutch modernist pioneer who transformed painting into pure abstraction. He developed Neoplasticism, a philosophy that sought universal harmony through primary colors, black lines, and geometric grids. His work moved systematically from representation to complete abstraction, influenced by Cubism and Theosophy, establishing visual principles that would define 20th-century abstract art.",
        "focus_areas": [
            {"title": "Geometric Harmony", "description": "Evaluates balance between lines, planes, and negative space"},
            {"title": "Primary Color Mastery", "description": "Assesses sophisticated use of red, yellow, blue, and neutrals"},
            {"title": "Compositional Grid", "description": "Focuses on mathematical relationships and visual rhythm"}
        ]
    },
    "vangogh": {
        "bio": "Van Gogh was a post-impressionist master whose emotionally intense, expressionistic style revolutionized painting. Working with bold impasto brushwork, vivid colors, and dynamic compositions, he transformed personal anguish into transcendent visual poetry. Though largely unrecognized in his lifetime, his work profoundly influenced modern art and established the emotional authenticity of subjective expression as central to artistic vision.",
        "focus_areas": [
            {"title": "Expressive Brushwork", "description": "Evaluates emotional intensity through technique"},
            {"title": "Color as Emotion", "description": "Assesses use of bold, non-naturalistic palettes"},
            {"title": "Dynamic Composition", "description": "Focuses on movement, rhythm, and visual energy"}
        ]
    },
    "gehry": {
        "bio": "Gehry is a Canadian-American architect renowned for deconstructivist design that challenges architectural conventions. His sculptural buildings feature unconventional materials, fragmented forms, and bold spatial innovations. He rejects pure formalism in favor of expressive, playful structures that engage with their urban context, making architecture a dynamic art form rather than mere functional shelter.",
        "focus_areas": [
            {"title": "Spatial Dynamics", "description": "Analyzes flow, movement, and spatial relationships"},
            {"title": "Material Innovation", "description": "Evaluates unconventional materials and structural expression"},
            {"title": "Sculptural Form", "description": "Focuses on three-dimensional composition and visual boldness"}
        ]
    }
}

def update_advisors():
    """Update all advisors with comprehensive bios and focus areas."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        for advisor_id, data in ADVISOR_DATA.items():
            bio = data["bio"]
            focus_areas_json = json.dumps(data["focus_areas"])

            cursor.execute(
                "UPDATE advisors SET bio = ?, focus_areas = ? WHERE id = ?",
                (bio, focus_areas_json, advisor_id)
            )
            print(f"✅ Updated {advisor_id}: bio and {len(data['focus_areas'])} focus areas")

        conn.commit()
        conn.close()
        print(f"\n✅ Successfully updated all {len(ADVISOR_DATA)} advisors!")
        return True
    except Exception as e:
        print(f"❌ Error updating advisors: {e}")
        return False

if __name__ == "__main__":
    update_advisors()
