let currentProfessorRow = null;

// --- Edit Professor ---
document.querySelectorAll(".fa-edit").forEach((btn) => {
  btn.addEventListener("click", function () {
    const row = this.closest("tr");
    currentProfessorRow = row;
    const name = row.children[0].textContent;
    const dept = row.children[1].textContent;
    document.getElementById("editProfessorName").value = name;
    document.getElementById("editProfessorDept").value = dept;
    document.getElementById("editProfessorModal").style.display = "flex";
  });
});

function closeEditProfessorModal() {
  document.getElementById("editProfessorModal").style.display = "none";
}

function saveProfessorEdit() {
  if (currentProfessorRow) {
    currentProfessorRow.children[0].textContent =
      document.getElementById("editProfessorName").value;
    currentProfessorRow.children[1].textContent =
      document.getElementById("editProfessorDept").value;
    closeEditProfessorModal();
  }
}

// --- Delete Professor ---
document.querySelectorAll(".fa-trash-alt").forEach((btn) => {
  btn.addEventListener("click", function () {
    const row = this.closest("tr");
    const name = row.children[0].textContent;
    if (confirm(`Are you sure you want to delete ${name}?`)) {
      row.remove();
    }
  });
});

// --- Add Professor ---
document.querySelector(".add-professor-btn").addEventListener("click", function () {
  document.getElementById("addProfessorModal").style.display = "flex";
});

function closeAddProfessorModal() {
  document.getElementById("addProfessorModal").style.display = "none";
  document.getElementById("newProfessorName").value = "";
  document.getElementById("newProfessorDept").value = "";
}

function saveNewProfessor() {
  const name = document.getElementById("newProfessorName").value.trim();
  const dept = document.getElementById("newProfessorDept").value.trim();

  if (!name || !dept) {
    alert("Please enter both name and department.");
    return;
  }

  const tbody = document.querySelector(".professors-table tbody");
  const newRow = document.createElement("tr");
  newRow.innerHTML = `
    <td>${name}</td>
    <td>${dept}</td>
    <td>
      <div class="rating-cell">
        <i class="fas fa-star star-icon"></i>
        <span>0.0</span>
      </div>
    </td>
    <td>0</td>
    <td><span class="status-badge active">Active</span></td>
    <td>
      <div class="actions-cell">
        <button class="action-btn"><i class="far fa-eye"></i></button>
        <button class="action-btn"><i class="far fa-edit"></i></button>
        <button class="action-btn delete"><i class="far fa-trash-alt"></i></button>
      </div>
    </td>
  `;
  tbody.appendChild(newRow);
  closeAddProfessorModal();

  // Rebind edit/delete for new row
  newRow.querySelector(".fa-edit").addEventListener("click", function () {
    currentProfessorRow = newRow;
    document.getElementById("editProfessorName").value = name;
    document.getElementById("editProfessorDept").value = dept;
    document.getElementById("editProfessorModal").style.display = "flex";
  });

  newRow.querySelector(".fa-trash-alt").addEventListener("click", function () {
    if (confirm(`Are you sure you want to delete ${name}?`)) {
      newRow.remove();
    }
  });
}
