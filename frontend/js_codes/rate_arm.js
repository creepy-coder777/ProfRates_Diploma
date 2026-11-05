const scales = document.querySelectorAll('.scale');
const ratings = {};
const labels = [
    'Բոլորովին համաձայն չեմ',
    'Համաձայն չեմ',
    'Մասամբ համաձայն եմ',
    'Համաձայն եմ',
    'Լիովին համաձայն եմ'
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
        alert(`Խնդրում ենք պատասխանել բոլոր ${totalQuestions} հարցերին հաստատելուց առաջ։`);
        return;
    }

    // Show confirmation message
    alert('Շնորհակալություն գնահատելու համար! Ձեր գնահատականը հաստատվել է։');
    
    // Log ratings and review
    console.log('Ratings:', ratings);
    console.log('Review:', review);
    console.log('Total questions:', totalQuestions);
    console.log('Answered questions:', answeredQuestions);
    
    // Redirect to home_eng.html after a short delay
    setTimeout(() => {
        window.location.href = 'home_arm.html';
    }, 1500); // 1.5 second delay to show the alert
}