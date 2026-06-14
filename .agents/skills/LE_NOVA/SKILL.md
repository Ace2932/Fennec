```markdown
# LE_NOVA Development Patterns

> Auto-generated skill from repository analysis

## Overview
This skill provides guidance for contributing to the **LE_NOVA** repository, a TypeScript-based project with a focus on hardware and firmware co-development. The repository manages hardware schematic and PCB design files, firmware source code, and supporting documentation. This guide covers coding conventions, hardware/firmware update workflows, testing patterns, and common commands to streamline contributions.

## Coding Conventions

### File Naming
- **Style:** `snake_case`
- **Example:**  
  ```
  hardware_interface.ts
  main_controller.ts
  ```

### Import Style
- **Relative imports** are used for module resolution.
- **Example:**
  ```typescript
  import { calculate_checksum } from './utils/checksum';
  ```

### Export Style
- **Named exports** are preferred.
- **Example:**
  ```typescript
  // In hardware_interface.ts
  export function initialize_hardware() { ... }
  export const HARDWARE_VERSION = 'v6';
  ```

### Commit Messages
- **Freeform** style (no strict prefixes)
- **Average length:** ~73 characters
- **Example:**
  ```
  Update voltage regulator mapping for new PCB revision
  ```

## Workflows

### Hardware PCB Modification and Firmware Update
**Trigger:** When a hardware feature needs to be added or fixed, requiring both schematic/PCB changes and firmware updates.  
**Command:** `/hardware-update`

**Step-by-step:**
1. **Edit KiCad schematic** (`.kicad_sch`) to add or modify hardware connections.
   - Example: Add a new sensor input pin.
2. **Update PCB layout** (`.kicad_pcb`) to match schematic changes.
   - Example: Route traces to the new sensor pin.
3. **Re-generate and export new gerber files** for manufacturing.
   - Example: Use KiCad's plot function to create `nova_pcb_v6_logic_gerbers.zip`.
4. **Update documentation** to reflect hardware changes.
   - Edit `docs/master-bom.md` to add new components.
   - Update `docs/pre-power-on-validation.md` with new validation steps.
5. **Modify firmware source files** (`.h`/`.cpp`) to align with new hardware features.
   - Example: Update pin mappings in `hardware_config.h` and logic in `sensor_manager.cpp`.
   - Example code:
     ```cpp
     // hardware_config.h
     #define SENSOR_PIN 23

     // sensor_manager.cpp
     pinMode(SENSOR_PIN, INPUT);
     ```
6. **Verify design rule checks (DRC/ERC)** and update documentation as needed.
   - Document any new constraints or validation results.

**Files involved:**
- `hardware/pcb-mods/nova_pcb_v6_logic/*.kicad_sch`
- `hardware/pcb-mods/nova_pcb_v6_logic/*.kicad_pcb`
- `hardware/pcb-mods/nova_pcb_v6_logic/*gerbers.zip`
- `docs/master-bom.md`
- `docs/pre-power-on-validation.md`
- `firmware/teensy/firmware/src/*.h`
- `firmware/teensy/firmware/src/*.cpp`

**Frequency:** ~2x/month

---

## Testing Patterns

- **Test file pattern:** `*.test.*`
- **Testing framework:** Unknown (check for framework in project or use standard TypeScript test runners)
- **Example:**
  ```typescript
  // utils.test.ts
  import { calculate_checksum } from './utils/checksum';

  describe('calculate_checksum', () => {
    it('returns correct checksum for input', () => {
      expect(calculate_checksum([1, 2, 3])).toBe(6);
    });
  });
  ```

## Commands

| Command           | Purpose                                                      |
|-------------------|--------------------------------------------------------------|
| /hardware-update  | Start the hardware PCB modification and firmware update flow |

```
