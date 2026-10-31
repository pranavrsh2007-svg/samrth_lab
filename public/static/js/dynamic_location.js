/**
 * Dynamic Cascading Location Selector:
 * Sequence: Wing -> Floor -> Laboratory -> Computer
 */

function setupLocationSelector(config = {}) {
  const wingSelect = document.getElementById(config.wingSelectId || 'wing-select');
  const floorSelect = document.getElementById(config.floorSelectId || 'floor-select');
  const labSelect = document.getElementById(config.labSelectId || 'lab-select');
  const computerSelect = document.getElementById(config.computerSelectId || 'computer-select');
  const previewContainer = document.getElementById(config.previewId || 'computer-preview');
  const activeOnly = config.activeOnly !== false;

  if (!wingSelect || !floorSelect || !labSelect) return;

  // 1. Load Wings
  fetch('/api/wings')
    .then(res => res.json())
    .then(wings => {
      wingSelect.innerHTML = '<option value="">-- Select Wing --</option>';
      wings.forEach(w => {
        wingSelect.innerHTML += `<option value="${w.id}">${w.name} (${w.code})</option>`;
      });
      if (config.initialWing) {
        wingSelect.value = config.initialWing;
        wingSelect.dispatchEvent(new Event('change'));
      }
    })
    .catch(err => console.error('Error fetching wings:', err));

  // 2. On Wing Change -> Load Floors
  wingSelect.addEventListener('change', () => {
    const wingId = wingSelect.value;
    floorSelect.innerHTML = '<option value="">-- Select Floor --</option>';
    labSelect.innerHTML = '<option value="">-- Select Laboratory --</option>';
    floorSelect.disabled = !wingId;
    labSelect.disabled = true;

    if (computerSelect) {
      computerSelect.innerHTML = '<option value="">-- Select Computer --</option>';
      computerSelect.disabled = true;
    }
    if (previewContainer) previewContainer.style.display = 'none';

    if (!wingId) return;

    fetch(`/api/floors?wing_id=${wingId}`)
      .then(res => res.json())
      .then(floors => {
        floors.forEach(f => {
          floorSelect.innerHTML += `<option value="${f.id}">${f.name}</option>`;
        });
        if (config.initialFloor) {
          floorSelect.value = config.initialFloor;
          floorSelect.dispatchEvent(new Event('change'));
        }
      });
  });

  // 3. On Floor Change -> Load Laboratories
  floorSelect.addEventListener('change', () => {
    const floorId = floorSelect.value;
    labSelect.innerHTML = '<option value="">-- Select Laboratory --</option>';
    labSelect.disabled = !floorId;

    if (computerSelect) {
      computerSelect.innerHTML = '<option value="">-- Select Computer --</option>';
      computerSelect.disabled = true;
    }
    if (previewContainer) previewContainer.style.display = 'none';

    if (!floorId) return;

    fetch(`/api/laboratories?floor_id=${floorId}`)
      .then(res => res.json())
      .then(labs => {
        labs.forEach(l => {
          labSelect.innerHTML += `<option value="${l.id}">${l.name} (${l.lab_code}) - ${l.department}</option>`;
        });
        if (config.initialLab) {
          labSelect.value = config.initialLab;
          labSelect.dispatchEvent(new Event('change'));
        }
      });
  });

  // 4. On Laboratory Change -> Load Computers
  if (computerSelect) {
    labSelect.addEventListener('change', () => {
      const labId = labSelect.value;
      computerSelect.innerHTML = '<option value="">-- Select Computer --</option>';
      computerSelect.disabled = !labId;
      if (previewContainer) previewContainer.style.display = 'none';

      if (!labId) return;

      fetch(`/api/computers?lab_id=${labId}&active_only=${activeOnly ? '1' : '0'}`)
        .then(res => res.json())
        .then(computers => {
          if (computers.length === 0) {
            computerSelect.innerHTML = '<option value="">No available workstations in this lab</option>';
            return;
          }
          computers.forEach(c => {
            const statusBadge = c.operational_status !== 'Working' ? ` [${c.operational_status}]` : '';
            computerSelect.innerHTML += `<option value="${c.id}">${c.pc_number} (${c.computer_id_code})${statusBadge}</option>`;
          });
          if (config.initialComputer) {
            computerSelect.value = config.initialComputer;
            computerSelect.dispatchEvent(new Event('change'));
          }
        });
    });

    // 5. On Computer Change -> Fetch specifications preview
    if (previewContainer) {
      computerSelect.addEventListener('change', () => {
        const compId = computerSelect.value;
        if (!compId) {
          previewContainer.style.display = 'none';
          return;
        }

        fetch(`/api/computer/${compId}`)
          .then(res => res.json())
          .then(data => {
            if (data.error) return;
            const statusClass = {
              'Working': 'badge-success',
              'Fault Reported': 'badge-danger',
              'Under Repair': 'badge-warning',
              'Repaired': 'badge-primary',
              'Decommissioned': 'badge-secondary'
            }[data.operational_status] || 'badge-light';

            previewContainer.innerHTML = `
              <div class="card p-3 mt-3" style="background: var(--bg-surface-secondary); border: 1px dashed var(--border-color);">
                <div class="d-flex align-items-center justify-content-between mb-2">
                  <div class="fw-bold" style="color: var(--primary); font-size: 0.95rem;">
                    <i class="fa-solid fa-desktop me-1"></i> ${data.computer_id_code} (${data.pc_number})
                  </div>
                  <span class="badge ${statusClass}">${data.operational_status}</span>
                </div>
                <div style="font-size: 0.825rem; color: var(--text-muted); display: grid; grid-template-columns: 1fr 1fr; gap: 0.4rem;">
                  <div><strong>Brand & Model:</strong> ${data.brand} ${data.model}</div>
                  <div><strong>Serial:</strong> ${data.serial_number}</div>
                  <div><strong>Processor:</strong> ${data.processor}</div>
                  <div><strong>RAM & Storage:</strong> ${data.ram} | ${data.storage}</div>
                </div>
              </div>
            `;
            previewContainer.style.display = 'block';
          });
      });
    }
  }
}
