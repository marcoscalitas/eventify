new JustValidate('#eventForm', { errorLabelCssClass: ['field-error'] })
    .addField('#title', [
        { rule: 'required', errorMessage: 'Title is required.' },
    ])
    .addField('#description', [
        { rule: 'required', errorMessage: 'Description is required.' },
    ])
    .addField('#date', [
        { rule: 'required', errorMessage: 'Date is required.' },
        {
            validator: (value) => new Date(value) > new Date(),
            errorMessage: 'Date must be in the future.',
        },
    ])
    .addField('#time', [
        { rule: 'required', errorMessage: 'Time is required.' },
    ])
    .addField('#location', [
        { rule: 'required', errorMessage: 'Location is required.' },
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
    ]);
