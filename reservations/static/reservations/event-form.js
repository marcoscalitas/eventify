new JustValidate('#eventForm', { errorLabelCssClass: ['field-error'], validateBeforeSubmitting: true })
    .addField('#title', [
        { rule: 'required', errorMessage: 'Title is required.' },
    ])
    .addField('#description', [
        { rule: 'required', errorMessage: 'Description is required.' },
    ])
    .addField('#start_date', [
        { rule: 'required', errorMessage: 'Start date is required.' },
        {
            validator: (value) => new Date(value) > new Date(),
            errorMessage: 'Date must be in the future.',
        },
    ])
    .addField('#start_time', [
        { rule: 'required', errorMessage: 'Start time is required.' },
    ])
    .addField('#venue', [
        { rule: 'required', errorMessage: 'Venue is required.' },
    ])
    .addField('#capacity', [
        { rule: 'required', errorMessage: 'Capacity is required.' },
        { rule: 'minNumber', value: 1, errorMessage: 'Must be at least 1.' },
    ])
    .addField('#image', [
        {
            validator: () => validateImageFile('image'),
            errorMessage: 'Image must be JPEG, PNG, GIF or WebP and under 5 MB.',
        },
    ])
    .onSuccess((e) => e.target.submit());
