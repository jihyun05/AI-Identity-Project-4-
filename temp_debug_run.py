from pathlib import Path
import os
p = Path('config/run_visual_control_test.yaml')
print('CONFIG_PATH', p.resolve())
print('CONFIG_TEXT')
print(p.read_text())
print('PERSONA_EXISTS', Path('config/personas/student_yoo_grounded.yaml').exists())
print('PERSONA_DIR', [name for name in os.listdir('config/personas') if 'student_yoo' in name])
print('OUTPUT_EXISTS', Path('results_new/visual_consistency/student_yoo_test').exists())
