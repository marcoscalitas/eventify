document.addEventListener('DOMContentLoaded', () => {
    // Reserve
    const reserveBtn = document.getElementById('reserveBtn');
    if (reserveBtn) {
        reserveBtn.addEventListener('click', () => {
            postAction(reserveBtn, `/api/event/${reserveBtn.dataset.eventId}/reserve`)
            .then(data => {
                showToast(data.message);
                setTimeout(() => location.reload(), RELOAD_DELAY);
            });
        });
    }

    // Cancel
    const cancelBtn = document.getElementById('cancelBtn');
    if (cancelBtn) {
        cancelBtn.addEventListener('click', async () => {
            if (!await showConfirm('Cancel your reservation?')) return;
            postAction(cancelBtn, `/api/event/${cancelBtn.dataset.eventId}/cancel`)
            .then(data => {
                showToast(data.message);
                setTimeout(() => location.reload(), RELOAD_DELAY);
            });
        });
    }

    // Favorite toggle
    const favBtn = document.getElementById('favBtn');
    if (favBtn) {
        favBtn.addEventListener('click', () => {
            postAction(favBtn, `/api/event/${favBtn.dataset.eventId}/favorite`)
            .then(data => {
                favBtn.classList.toggle('btn-fav--active', data.favorited);
                favBtn.textContent = data.favorited ? '♥ Favorited' : '♡ Favorite';
                showToast(data.favorited ? 'Added to favorites' : 'Removed from favorites');
            });
        });
    }

    // Star rating
    let selectedRating = 0;
    const starRating = document.getElementById('starRating');
    if (starRating) {
        starRating.querySelectorAll('button').forEach(star => {
            star.addEventListener('click', () => {
                selectedRating = parseInt(star.dataset.value);
                starRating.querySelectorAll('button').forEach((s, i) => {
                    s.classList.toggle('active', i < selectedRating);
                });
            });
        });
    }

    // Submit review
    const submitReview = document.getElementById('submitReview');
    if (submitReview) {
        submitReview.addEventListener('click', () => {
            if (selectedRating === 0) return showToast('Please select a rating.', 'error');
            const comment = document.getElementById('reviewComment').value;
            setLoading(submitReview, true);
            safeFetch(`/api/event/${submitReview.dataset.eventId}/review`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ rating: selectedRating, comment }),
            })
            .then(data => {
                showToast(data.message);
                const noReviews = document.getElementById('noReviews');
                if (noReviews) noReviews.remove();
                const reviewsList = document.getElementById('reviewsList');
                const review = data.review;
                reviewsList.insertAdjacentHTML('afterbegin', `
                    <div class="review">
                        <div class="review__header">
                            <strong>${escapeHtml(review.username)}</strong>
                            <span class="review__stars">${review.rating}★</span>
                            <span class="review__date">${escapeHtml(review.created_at)}</span>
                        </div>
                        ${review.comment ? `<p class="review__comment">${escapeHtml(review.comment)}</p>` : ''}
                    </div>
                `);
                document.getElementById('reviewForm').remove();
            })
            .catch(err => {
                showToast(err.message, 'error');
                setLoading(submitReview, false);
            });
        });
    }
});
