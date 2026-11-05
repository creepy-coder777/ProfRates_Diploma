// Open modal when any "Add Question" button is clicked
document.querySelectorAll(".add-question-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.getElementById("addQuestionModal").style.display = "flex";
    document.getElementById("questionText").value = "";
    // reset mode to add
    saveNewQuestion.mode = "add";
    saveNewQuestion.target = null;
  });
});

// Close modal
function closeAddQuestionModal() {
  document.getElementById("addQuestionModal").style.display = "none";
  document.getElementById("questionText").value = "";
}

// Save new or edited question
function saveNewQuestion() {
  const text = document.getElementById("questionText").value.trim();
  if (!text) {
    alert("Please enter a question.");
    return;
  }

  if (saveNewQuestion.mode === "edit" && saveNewQuestion.target) {
    // Editing existing question
    saveNewQuestion.target.querySelector(".question-content").textContent = text;
  } else {
    // Adding new question to the first category for demo
    const category = document.querySelector(".category-card");
    const questionCount = category.querySelectorAll(".question-item").length + 1;

    const newQuestion = document.createElement("div");
    newQuestion.classList.add("question-item");
    newQuestion.innerHTML = `
      <div class="question-header">
        <div class="question-text">
          <span class="question-number">${questionCount}.</span>
          <span class="question-content">${text}</span>
        </div>
        <div class="question-actions">
          <button class="action-btn edit"><i class="far fa-edit"></i></button>
          <button class="action-btn delete"><i class="far fa-trash-alt"></i></button>
        </div>
      </div>
      <div class="rating-scale">
        <span class="rating-label">Rating Scale:</span>
        <div class="scale-buttons">
          <button class="scale-btn">1</button>
          <button class="scale-btn">2</button>
          <button class="scale-btn">3</button>
          <button class="scale-btn">4</button>
          <button class="scale-btn">5</button>
        </div>
      </div>
    `;
    category.appendChild(newQuestion);

    bindQuestionActions(newQuestion);
  }

  closeAddQuestionModal();
}

// Bind edit/delete actions
function bindQuestionActions(questionItem) {
  const editBtn = questionItem.querySelector(".edit");
  const deleteBtn = questionItem.querySelector(".delete");

  editBtn.addEventListener("click", () => {
    const contentSpan = questionItem.querySelector(".question-content");
    document.getElementById("questionText").value = contentSpan.textContent;
    document.getElementById("addQuestionModal").style.display = "flex";
    saveNewQuestion.mode = "edit";
    saveNewQuestion.target = questionItem;
  });

  deleteBtn.addEventListener("click", () => {
    if (confirm("Delete this question?")) {
      questionItem.remove();
    }
  });
}

// Initialize existing questions
document.querySelectorAll(".question-item").forEach(item => bindQuestionActions(item));
