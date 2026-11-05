let currentProfessorRow = null;

// --- Edit Professor ---
document.querySelectorAll(".fa-edit").forEach((btn) => {
  btn.addEventListener("click", function () {
    const row = this.closest("tr");
    currentProfessorRow = row;
    const name = row.children[0].textContent;
    const department = row.children[1].textContent;
    document.getElementById("editProfessorName").value = name;
    document.getElementById("editProfessorEmail").value = department;
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
      document.getElementById("editProfessorEmail").value;
    closeEditProfessorModal();
  }
}

// --- Delete Professor ---
document.querySelectorAll(".fa-trash-alt").forEach((btn) => {
  btn.addEventListener("click", function () {
    const row = this.closest("tr");
    const name = row.children[0].textContent;
    if (confirm(`Վստա՞հ եք, որ ցանկանում եք ջնջել ${name}-ին`)) {
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
  document.getElementById("newProfessorEmail").value = "";
}

function saveNewProfessor() {
  const name = document.getElementById("newProfessorName").value.trim();
  const department = document.getElementById("newProfessorEmail").value.trim();

  if (!name || !department) {
    alert("Խնդրում ենք լրացնել անունը և ամբիոնը։");
    return;
  }

  const tbody = document.querySelector(".professors-table tbody");
  const newRow = document.createElement("tr");
  newRow.innerHTML = `
    <td>${name}</td>
    <td>${department}</td>
    <td>
      <div class="rating-cell">
        <i class="fas fa-star star-icon"></i>
        <span>0.0</span>
      </div>
    </td>
    <td>0</td>
    <td><span class="status-badge active">Ակտիվ</span></td>
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
    document.getElementById("editProfessorEmail").value = department;
    document.getElementById("editProfessorModal").style.display = "flex";
  });

  newRow.querySelector(".fa-trash-alt").addEventListener("click", function () {
    if (confirm(`Վստա՞հ եք, որ ցանկանում եք ջնջել ${name}-ին`)) {
      newRow.remove();
    }
  });
}
