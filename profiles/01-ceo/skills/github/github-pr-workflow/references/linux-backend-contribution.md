# Contributing Linux Backends to Windows-First Projects

## Pattern: Windows → Linux Desktop Integration

**Use case:** Project uses Windows-specific APIs (WorkerW, Win32) for desktop integration. Linux needs X11/Wayland alternatives.

### Analysis Checklist

1. **Find platform-specific code**
   ```bash
   grep -r "windows_sys\|Win32\|WorkerW" --include="*.rs"
   ```

2. **Identify what it does**
   - WorkerW = embed window behind desktop icons
   - RegisterHotKey = global hotkeys
   - HKCU Run = autostart
   - System tray (usually cross-platform)

3. **Linux alternatives**
   | Windows API | X11 Alternative | Wayland Alternative |
   |-------------|----------------|---------------------|
   | WorkerW embed | `_NET_WM_WINDOW_TYPE_DESKTOP` property | Layer shell (compositor-specific) |
   | RegisterHotKey | `XGrabKey()` | No standard (use UI fallback) |
   | HKCU Run | `~/.config/autostart/*.desktop` | Same |
   | System tray | AppIndicator (cross-platform crate works) | Same |

### Rust Cross-Platform Structure

**Recommended:**
```
src/
  main.rs         # Dispatcher: #[cfg(target_os = "...")]
  common.rs       # Shared logic
  windows.rs      # Win32 code
  linux.rs        # X11/Wayland code
```

**Cargo.toml:**
```toml
[target.'cfg(target_os = "linux")'.dependencies]
x11rb = "0.13"
```

### Common Build Issues

**Missing system libs:**
```bash
# Debian/Ubuntu
sudo apt-get install libgtk-3-dev libwebkit2gtk-4.1-dev \
  libayatana-appindicator3-dev libxdo-dev

# Fedora/RHEL
sudo dnf install gtk3-devel webkit2gtk4.1-devel \
  libappindicator-gtk3-devel
```

**Rust version too old:**
- Check error: "rustc X.Y.Z is not supported by..."
- Update: `rustup update stable && rustup default stable`

**Lifetime issues in closures:**
- Symptom: "closure may outlive current function"
- Fix: Add `move` keyword or clone/Arc wrap captured values
- Common in event loops where closure outlives owner

### X11 Desktop Window Pattern

```rust
use x11rb::connection::Connection;
use x11rb::protocol::xproto::*;

// Set window type to desktop layer
let atoms = x11rb::atom_manager::AtomCollection::new(&conn)?;
conn.change_property32(
    PropMode::REPLACE,
    window,
    atoms._NET_WM_WINDOW_TYPE,
    AtomEnum::ATOM,
    &[atoms._NET_WM_WINDOW_TYPE_DESKTOP],
)?;
```

### Contribution Strategy

**Phase approach for large features:**
1. **MVP** - Standalone window (no desktop embed), prove it works
2. **X11 layer** - Desktop embedding on X11-based DEs
3. **Refinements** - Hotkeys, multi-monitor, resolution changes
4. **Wayland** (optional) - Compositor-specific (Sway, KDE, GNOME)

**Why phased:**
- Shows you can deliver (builds trust)
- Each phase = mergeable PR
- Faster feedback cycle
- Long-term Wayland can wait

**Communication:**
- Draft PR early with "WIP: Linux support Phase 1"
- Video demo > long description
- Document limitations clearly ("Phase 1: no desktop embed yet")
- Ask for feedback, don't wait for perfection

### Pitfalls

❌ **Don't:** Start with Wayland (too compositor-specific, blocks progress)  
✅ **Do:** X11 first (works on 80% of Linux desktops)

❌ **Don't:** Guess at Windows code behavior  
✅ **Do:** Read Windows implementation, understand what it does, then find Linux equivalent

❌ **Don't:** Submit giant "add full Linux support" PR  
✅ **Do:** Break into phases, merge incrementally

❌ **Don't:** Hardcode paths like `/usr/bin/godot`  
✅ **Do:** Use environment variables, search PATH, document config

---

**Sources:**
- BagIdea Office Linux contribution (2026-06-10)
- X11 spec: https://specifications.freedesktop.org/wm-spec/
- x11rb: https://docs.rs/x11rb/
