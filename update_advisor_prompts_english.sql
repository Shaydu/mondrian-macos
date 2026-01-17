-- Update all advisor prompts to explicitly require English output

UPDATE advisors SET prompt = '**IMPORTANT: ALL ANALYSIS MUST BE IN ENGLISH ONLY**

' || prompt 
WHERE prompt NOT LIKE '%ENGLISH%';
