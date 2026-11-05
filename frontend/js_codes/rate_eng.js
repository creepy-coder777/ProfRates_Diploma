const scales = document.querySelectorAll('.scale');
const ratings = {};
const labels = [
    'Strongly Disagree',
    'Disagree',
    'Neither agree nor Disagree',
    'Agree',
    'Strongly Agree'
];

scales.forEach((scale, index) => {
    const segments = scale.querySelectorAll('.segment');
    const questionNum = scale.dataset.question;
    const textElement = scale.parentElement.querySelector('.selected-text');

    segments.forEach(segment => {
        segment.addEventListener('click', () => {
            const value = parseInt(segment.dataset.value);
            ratings[questionNum] = value;

            segments.forEach(seg => {
                seg.classList.remove('pos-1', 'pos-2', 'pos-3', 'pos-4', 'pos-5');
            });

            segments.forEach((seg, i) => {
                if (i < value) {
                    seg.classList.add(`pos-${i + 1}`);
                }
            });

            // Update label text
            if (textElement) {
                textElement.textContent = labels[value - 1];
            }
        });
    });
});

const reviewText = document.getElementById('reviewText');
const charCount = document.getElementById('charCount');

reviewText.addEventListener('input', () => {
    charCount.textContent = reviewText.value.length;
});

function submitRating() {
    const review = reviewText.value;
    const totalQuestions = scales.length; // Dynamic calculation
    const answeredQuestions = Object.keys(ratings).length;

    if (answeredQuestions < totalQuestions) {
        alert(`Please answer all ${totalQuestions} questions before submitting.`);
        return;
    }

    // Show confirmation message
    alert('Thank you for your rating! Your review has been submitted.');
    
    // Log ratings and review
    console.log('Ratings:', ratings);
    console.log('Review:', review);
    console.log('Total questions:', totalQuestions);
    console.log('Answered questions:', answeredQuestions);
    
    // Redirect to home_eng.html after a short delay
    setTimeout(() => {
        window.location.href = 'home_eng.html';
    }, 1500); // 1.5 second delay to show the alert
}