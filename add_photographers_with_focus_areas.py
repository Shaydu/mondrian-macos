#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Add/Update Photographers to Database with Focus Areas
Enhanced with aesthetic prompts that channel each photographer's unique vision
"""
import sqlite3
import json

def get_db_connection():
    conn = sqlite3.connect("mondrian/mondrian.db")
    conn.row_factory = sqlite3.Row
    return conn

def add_focus_areas_column():
    """Add focus_areas column to advisors table if it doesn't exist"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if focus_areas column exists
        cursor.execute("PRAGMA table_info(advisors)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'focus_areas' not in columns:
            cursor.execute("ALTER TABLE advisors ADD COLUMN focus_areas TEXT")
            print("✅ Added focus_areas column to advisors table")
        else:
            print("ℹ️ focus_areas column already exists")
            
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Error adding focus_areas column: {e}")
        conn.close()
        return False

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
    print("📸 Adding/Updating Photographers to Database with Focus Areas")
    print("=" * 60)
    
    # First, ensure the database has the focus_areas column
    print("Step 1: Ensuring database schema...")
    if not add_focus_areas_column():
        print("❌ Failed to update database schema")
        return
    
    print("\nStep 2: Adding photographers...")
    conn = get_db_connection()
    
    # Enhanced aesthetic prompts with focus area integration
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
            "prompt": "Analyze this photograph through the lens of Ansel Adams' profound environmental consciousness and Zone System precision. As someone who saw the viewfinder as a tool of conservation, evaluate how this image captures the dramatic tonal contrasts and sublime nature that inspired his conservation efforts. Focus specifically on:\n\n**Zone System Precision**: How well does this photograph demonstrate mastery of tonal range and exposure?\n**Environmental Consciousness**: Does this image convey the connection to landscape preservation that drove Adams' advocacy?\n**Dramatic Composition**: Does the composition achieve the powerful visual impact and sense of scale that made his work conservation tools?\n\nProvide numeric grades 0-10. For each dimension, include:\n\n- **Comment**: brief <100 word explanation of the grade\n- **Recommendation**: actionable advice specific to this image\n\nOutput only a Markdown table. Exclude model reasoning unless `thinking` is enabled.\n\n| Dimension | Grade (0-10) | Comment | Recommendation |\n|-----------|---------------|---------|----------------|\n| use of tonal range | | | |\n| composition mastery | | | |\n| emotional impact | | | |\n| conservation message | | | |\n| technical excellence | | | |\n| visual storytelling | | | |\n| light and shadow | | | |\n| perspective/depth | | | |"
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
            "prompt": "Analyze this photograph through the lens of Carleton Watkins' pioneering spirit, seeing the sublime grandeur that would inspire national preservation. As the photographer whose images helped establish Yosemite as America's first protected wilderness, evaluate how this photograph captures the monumental scale and pristine beauty that moved Congress to preserve our national treasures. Focus specifically on:\n\n**Monumental Scale**: Does this image convey the sense of grandeur and expansive vision that inspired Watkins?\n**Conservation Impact**: Could this photograph inspire the preservation efforts that made his work historically significant?\n**Pioneering Technique**: Does the technical execution reflect the large-format precision that defined his approach?\n\nProvide numeric grades 0-10. For each dimension, include:\n\n- **Comment**: brief <100 word explanation of the grade\n- **Recommendation**: actionable advice specific to this image\n\nOutput only a Markdown table. Exclude model reasoning unless `thinking` is enabled.\n\n| Dimension | Grade (0-10) | Comment | Recommendation |\n|-----------|---------------|---------|----------------|\n| monumental scale | | | |\n| wilderness grandeur | | | |\n| conservation impact | | | |\n| technical precision | | | |\n| visual awe | | | |\n| historical significance | | | |\n| composition strength | | | |\n| preservation message | | | |"
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
            "prompt": "Analyze this photograph through the lens of Edward Weston's modernist vision, seeing beyond literal representation to reveal the essence of light, form, and structure. As a photographer who taught us that landscapes could be abstract compositions as powerful as his famous still lifes, evaluate how this image demonstrates the clarity, tonal precision, and formal strength that made his California coast and desert work revolutionary. Focus specifically on:\n\n**Modernist Clarity**: Does this photograph achieve the sharp focus and formal precision that defined Weston's modernist approach?\n**Abstract Vision**: Can you see beyond literal representation to the essence of light, form, and structure?\n**Form and Structure**: Does the composition achieve the pure visual poetry that influenced generations?\n\nProvide numeric grades 0-10. For each dimension, include:\n\n- **Comment**: brief <100 word explanation of the grade\n- **Recommendation**: actionable advice specific to this image\n\nOutput only a Markdown table. Exclude model reasoning unless `thinking` is enabled.\n\n| Dimension | Grade (0-10) | Comment | Recommendation |\n|-----------|---------------|---------|----------------|\n| modernist clarity | | | |\n| abstract vision | | | |\n| formal strength | | | |\n| tonal precision | | | |\n| compositional poetry | | | |\n| visual essence | | | |\n| sharp focus | | | |\n| artistic impact | | | |"
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
            "prompt": "Analyze this photograph through the lens of Imogen Cunningham's sharp-focus intimacy, finding profound beauty in the intricate details of natural forms. As a key member of Group f/64 who brought the same botanical precision to landscapes that she applied to her famous plant studies, evaluate how this image demonstrates the unmanipulated, direct representation and technical rigor that defined the sharp-focus modernist approach. Focus specifically on:\n\n**Botanical Intimacy**: Does this photograph demonstrate the close observation of natural forms that made her botanical work legendary?\n**Sharp-Focus Modernism**: Does the technical precision and clarity reflect the Group f/64 aesthetic?\n**Group f/64 Aesthetics**: Is this an example of direct, unmanipulated representation?\n\nProvide numeric grades 0-10. For each dimension, include:\n\n- **Comment**: brief <100 word explanation of the grade\n- **Recommendation**: actionable advice specific to this image\n\nOutput only a Markdown table. Exclude model reasoning unless `thinking` is enabled.\n\n| Dimension | Grade (0-10) | Comment | Recommendation |\n|-----------|---------------|---------|----------------|\n| botanical intimacy | | | |\n| sharp focus | | | |\n| observational precision | | | |\n| formal beauty | | | |\n| technical rigor | | | |\n| natural detail | | | |\n| modernist approach | | | |\n| hidden beauty | | | |"
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
            "prompt": "Analyze this photograph through the lens of Laura Gilpin's lyrical Southwest spirit, honoring both landscape and the human stories within it. As a photographer who expanded landscape photography beyond pure wilderness to include cultural landscapes, evaluate how this image demonstrates the formal elegance and deep cultural respect that made her Navajo photography so powerful. Focus specifically on:\n\n**Cultural Respect**: Does this photograph demonstrate the ethical representation and cultural sensitivity that honored Navajo communities?\n**Lyrical Southwest Spirit**: Does the image achieve the emotional resonance with landscape that defined her work?\n**Formal Elegance**: Is there compositional grace and visual poetry in the execution?\n\nProvide numeric grades 0-10. For each dimension, include:\n\n- **Comment**: brief <100 word explanation of the grade\n- **Recommendation**: actionable advice specific to this image\n\nOutput only a Markdown table. Exclude model reasoning unless `thinking` is enabled.\n\n| Dimension | Grade (0-10) | Comment | Recommendation |\n|-----------|---------------|---------|----------------|\n| cultural respect | | | |\n| emotional resonance | | | |\n| formal elegance | | | |\n| ethical sensitivity | | | |\n| lyrical spirit | | | |\n| compositional grace | | | |\n| landscape poetry | | | |\n| human dignity | | | |"
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
    print("\nNew photographers available with enhanced focus areas:")
    for photographer in photographers:
        focus_areas = ", ".join([fa["title"] for fa in photographer["focus_areas"]])
        print(f"  • {photographer['name']} ({photographer['id']})")
        print(f"    Focus: {focus_areas}")

if __name__ == "__main__":
    main()
