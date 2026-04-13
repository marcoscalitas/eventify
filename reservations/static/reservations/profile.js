new JustValidate('#profileForm', { errorLabelCssClass: ['field-error'] })
    .addField('#email', [
        { rule: 'email', errorMessage: 'Enter a valid email.' },
    ])
    .addField('#avatar', [
        {
            validator: () => validateImageFile('avatar'),
            errorMessage: 'Allowed: JPG, PNG, GIF, WebP (max 5 MB).',
        },
    ])
    .onSuccess((e) => e.target.submit());
