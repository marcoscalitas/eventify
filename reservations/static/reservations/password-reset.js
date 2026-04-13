new JustValidate('#resetForm', { errorLabelCssClass: ['field-error'] })
    .addField('#id_email', [
        { rule: 'required', errorMessage: 'Email is required.' },
        { rule: 'email', errorMessage: 'Enter a valid email.' },
    ])
    .onSuccess((e) => e.target.submit());
