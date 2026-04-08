new JustValidate('#registerForm', { errorLabelCssClass: ['field-error'] })
    .addField('#username', [
        { rule: 'required', errorMessage: 'Username is required.' },
        { rule: 'minLength', value: 3, errorMessage: 'At least 3 characters.' },
        { rule: 'maxLength', value: 150, errorMessage: 'At most 150 characters.' },
    ])
    .addField('#email', [
        { rule: 'required', errorMessage: 'Email is required.' },
        { rule: 'email', errorMessage: 'Enter a valid email.' },
    ])
    .addField('#password', [
        { rule: 'required', errorMessage: 'Password is required.' },
        { rule: 'minLength', value: 6, errorMessage: 'At least 6 characters.' },
    ])
    .addField('#confirmation', [
        { rule: 'required', errorMessage: 'Confirm your password.' },
        {
            validator: (value) => value === document.getElementById('password').value,
            errorMessage: 'Passwords do not match.',
        },
    ])
    .addField('#role', [
        { rule: 'required', errorMessage: 'Select a role.' },
    ]);
