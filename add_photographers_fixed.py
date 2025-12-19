#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Add/Update Photographers to Database
Enhanced with aesthetic prompts that channel each photographer's unique vision
"""
import sqlite3
import json

def get_db_connection():
    conn = sqlite3.connect("mondrian.db")
    conn.row_factory = sqlite3.Row
    return conn

def add_photographer(conn, advisor_id, name, bio, years, category, focus_areas, prompt):
    """Add or update a photographer advisor to the database"""
    cursor = conn.cursor()
    
    # Insert or update advisor
    cursor.execute("""
        INSERT OR REPLACE INTO advisors (id, name, bio, years, prompt, focus_areas, category)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (advisor_id, name, bio, years, prompt, json.dumps(focus_areas), category))
    
    print(f"✅ Added/Updated: {name} ({advisor_id})")
    return True

def main():
    print("📸 Adding/Updating Photographers to Database")
    print("=" * 50)
    
    conn = get_db_connection()
    
    # Enhanced aesthetic prompts for each photographer
    photographers = [
        {
            "id": "ansel",
            "name": "Ansel Adams",
            "bio": "Adams is the most iconic landscape photographer of the 20th century, best known for his dramatic black-and-white images of the American West, especially Yosemite. He co-developed the Zone System, which revolutionized photographic exposure and printing, and used photography as a powerful tool for environmental conservation.",
            "years": "1902-1984",
            "category": "Photographer",
            "focus_areas": [
                {"title": "Zone System Precision", "description": "Evaluates tonal range and exposure mastery"},
                {"title": "Environmental Consciousness", "description": "Assesses connection to landscape preservation"},
                {"title": "Dramatic Composition", "description": "Focuses on powerful visual impact and scale"}
            ],
            "prompt": "Analyze this photograph through the lens of Ansel Adams' profound environmental consciousness and Zone System precision. As someone who saw the viewfinder as a tool of conservation, evaluate how this image captures the dramatic tonal contrasts and sublime nature that inspired his conservation efforts. Focus on the mastery of light, the power of composition to convey the majesty of the American landscape, and whether this photograph could inspire the same sense of awe that drove his advocacy for preserving wild places. Provide numeric grades 0-10. For each dimension, include:\n\n- **Comment**: brief <100 word explanation of the grade\n- **Recommendation**: actionable advice specific to this image\n\nOutput only a Markdown table. Exclude model reasoning unless `thinking` is enabled.\n\n| Dimension | Grade (0-10) | Comment | Recommendation |\n|-----------|---------------|---------|----------------|\n| use of tonal range | | | |\n| composition mastery | | | |\n| emotional impact | | | |\n| conservation message | | | |\n| technical excellence | | | |\n| visual storytelling | | | |\n| light and shadow | | | |\n| perspective/depth | | | |"
        },
        {
            "id": "watkins",
            "name": "Carleton Watkins",
            "bio": "Watkins was a pioneer of large-format landscape photography in the 19th century, producing monumental images of Yosemite and the American frontier. His photographs were instrumental in convincing Congress to protect Yosemite, helping lay the groundwork for the U.S. National Park system.",
            "years": "1829-1916",
            "category": "Photographer",
            "focus_areas": [
                {"title": "Monumental Scale", "description": "Evaluates sense of grandeur and expansive vision"},
                {"title": "Conservation Impact", "description": "Assesses ability to inspire preservation"},
                {"title": "Pioneering Technique", "description": "Focuses on large-format precision and clarity"}
            ],
            "prompt": "Analyze this photograph through the lens of Carleton Watkins' pioneering spirit, seeing the sublime grandeur that would inspire national preservation. As the photographer whose images helped establish Yosemite as America's first protected wilderness, evaluate how this photograph captures the monumental scale and pristine beauty that moved Congress to preserve our national treasures. Focus on the technical mastery of large-format photography, the sense of awe-inspiring wilderness, and whether this image carries the same power to inspire conservation that made Watkins' work historically significant. Provide numeric grades 0-10. For each dimension, include:\n\n- **Comment**: brief <100 word explanation of the grade\n- **Recommendation**: actionable advice specific to this image\n\nOutput only a Markdown table. Exclude model reasoning unless `thinking` is enabled.\n\n| Dimension | Grade (0-10) | Comment | Recommendation |\n|-----------|---------------|---------|----------------|\n| monumental scale | | | |\n| wilderness grandeur | | | |\n| conservation impact | | | |\n| technical precision | | | |\n| visual awe | | | |\n| historical significance | | | |\n| composition strength | | | |\n| preservation message | | | |"
        },
        {
            "id": "weston",
            "name": "Edward Weston",
            "bio": "Though often associated with still lifes and nudes, Weston's landscapes—especially of the California coast and deserts—are foundational to modernist photography. His work emphasized clarity, form, and tonal precision, influencing generations of photographers to see landscapes as abstract compositions as well as places.",
            "years": "1886-1958",
            "category": "Photographer",
            "focus_areas": [
                {"title": "Modernist Clarity", "description": "Evaluates sharp focus and formal precision"},
                {"title": "Abstract Vision", "description": "Assesses ability to see beyond literal representation"},
                {"title": "Form and Structure", "description": "Focuses on composition as pure visual poetry"}
            ],
            "prompt": "Analyze this photograph through the lens of Edward Weston's modernist vision, seeing beyond literal representation to reveal the essence of light, form, and structure. As a photographer who taught us that landscapes could be abstract compositions as powerful as his famous still lifes, evaluate how this image demonstrates the clarity, tonal precision, and formal strength that made his California coast and desert work revolutionary. Focus on whether this photograph achieves the sharp-focus intimacy and visual poetry that influenced generations to see photography as high art. Provide numeric grades 0-10. For each dimension, include:\n\n- **Comment**: brief <100 word explanation of the grade\n- **Recommendation**: actionable advice specific to this image\n\nOutput only a Markdown table. Exclude model reasoning unless `thinking` is enabled.\n\n| Dimension | Grade (0-10) | Comment | Recommendation |\n|-----------|---------------|---------|----------------|\n| modernist clarity | | | |\n| abstract vision | | | |\n| formal strength | | | |\n| tonal precision | | | |\n| compositional poetry | | | |\n| visual essence | | | |\n| sharp focus | | | |\n| artistic impact | | | |"
        },
        {
            "id": "cunningham",
            "name": "Imogen Cunningham",
            "bio": "Cunningham was a key member of Group f/64 alongside Ansel Adams and Edward Weston. While celebrated for botanical studies and portraits, her landscapes and nature photographs helped define a sharp-focus, modernist approach that treated the natural world with intimacy and rigor.",
            "years": "1883-1976",
            "category": "Photographer",
            "focus_areas": [
                {"title": "Botanical Intimacy", "description": "Evaluates close observation of natural forms"},
                {"title": "Sharp-Focus Modernism", "description": "Assesses technical precision and clarity"},
                {"title": "Group f/64 Aesthetics", "description": "Focuses on direct, unmanipulated representation"}
            ],
            "prompt": "Analyze this photograph through the lens of Imogen Cunningham's sharp-focus intimacy, finding profound beauty in the intricate details of natural forms. As a key member of Group f/64 who brought the same botanical precision to landscapes that she applied to her famous plant studies, evaluate how this image demonstrates the unmanipulated, direct representation and technical rigor that defined the sharp-focus modernist approach. Focus on the intimacy of observation, the clarity of form, and whether this photograph achieves the same sense of discovering hidden beauty in the natural world that made her botanical work legendary. Provide numeric grades 0-10. For each dimension, include:\n\n- **Comment**: brief <100 word explanation of the grade\n- **Recommendation**: actionable advice specific to this image\n\nOutput only a Markdown table. Exclude model reasoning unless `thinking` is enabled.\n\n| Dimension | Grade (0-10) | Comment | Recommendation |\n|-----------|---------------|---------|----------------|\n| botanical intimacy | | | |\n| sharp focus | | | |\n| observational precision | | | |\n| formal beauty | | | |\n| technical rigor | | | |\n| natural detail | | | |\n| modernist approach | | | |\n| hidden beauty | | | |"
        },
        {
            "id": "gilpin",
            "name": "Laura Gilpin",
            "bio": "Gilpin is best known for her lyrical photographs of the American Southwest, particularly Navajo lands and communities. Her landscapes combine formal elegance with deep cultural respect, expanding the emotional and ethical scope of landscape photography beyond pure wilderness imagery.",
            "years": "1891-1979",
            "category": "Photographer",
            "focus_areas": [
                {"title": "Cultural Respect", "description": "Evaluates ethical representation and cultural sensitivity"},
                {"title": "Lyrical Southwest Spirit", "description": "Assesses emotional resonance with landscape"},
                {"title": "Formal Elegance", "description": "Focuses on compositional grace and visual poetry"}
            ],
            "prompt": "Analyze this photograph through the lens of Laura Gilpin's lyrical Southwest spirit, honoring both landscape and the human stories within it. As a photographer who expanded landscape photography beyond pure wilderness to include cultural landscapes, evaluate how this image demonstrates the formal elegance and deep cultural respect that made her Navajo photography so powerful. Focus on whether this photograph achieves the emotional resonance and ethical sensitivity that honored both the beauty of the land and the dignity of its people. Provide numeric grades 0-10. For each dimension, include:\n\n- **Comment**: brief <100 word explanation of the grade\n- **Recommendation**: actionable advice specific to this image\n\nOutput only a Markdown table. Exclude model reasoning unless `thinking` is enabled.\n\n| Dimension | Grade (0-10) | Comment | Recommendation |\n|-----------|---------------|---------|----------------|\n| cultural respect | | | |\n| emotional resonance | | | |\n| formal elegance | | | |\n| ethical sensitivity | | | |\n| lyrical spirit | | | |\n| compositional grace | | | |\n| landscape poetry | | | |\n| human dignity | | | |"
        }
    ]
    
    # Add each photographer
    for photographer in photographers:
        try:
            add_photographer(
                conn, 
                photographer["id"],
                photographer["name"],
                photographer["bio"],
                photographer["years"],
                photographer["category"],
                photographer["focus_areas"],
                photographer["prompt"]
            )
        except Exception as e:
            print(f"❌ Error adding {photographer['name']}: {e}")
    
    # Commit changes
    conn.commit()
    conn.close()
    
    print("\n🎉 All photographers added/updated successfully!")
    print("\nNew photographers available:")
    for photographer in photographers:
        print(f"  • {photographer['name']} ({photographer['id']})")

if __name__ == "__main__":
    main()
