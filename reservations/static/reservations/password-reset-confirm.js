new JustValidate('#resetConfirmForm', { errorLabelCssClass: ['field-error'] })
    .addField('#id_new_password1', [
        { rule: 'required', errorMessage: 'Password is required.' },
        { rule: 'minLength', value: 6, errorMessage: 'At least 6 characters.' },
    ])
    .addField('#id_new_password2', [
        { rule: 'required', errorMessage: 'Confirm your password.' },
        {
            validator: (value) => value === document.getElementById('id_new_password1').value,
            errorMessage: 'Passwords do not match.',
        },
    ])
    .onSuccess((e) => e.target.submit());
