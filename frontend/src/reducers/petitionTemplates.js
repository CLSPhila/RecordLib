import { createSlice, combineReducers } from '@reduxjs/toolkit'
import { FETCH_USER_PROFILE_SUCCEEDED } from "frontend/src/actions/user"

const insertTemplate = (state, action) => {
    const {id, name} = action.payload
    return {...state, [id]: {id: id, name: name}}
}

const expungementTemplateSlice = createSlice({
    name: 'expungementTemplates',
    initialState: {},
    reducers: {
        insert: insertTemplate,
    },
    extraReducers: {
        FETCH_USER_PROFILE_SUCCEEDED: (state, action) => {
            const { expungement_petition_template_options } = action.payload
            return Object.assign({}, expungement_petition_template_options)
        }
    }
})

const sealingTemplateSlice = createSlice({
    name: 'sealingTemplates',
    initialState: {},
    reducers: {
        insert: insertTemplate,
    },
    extraReducers: {
        FETCH_USER_PROFILE_SUCCEEDED: (state, action) => {
            // Reducer to just overwrite any stored templates with 
            const { sealing_petition_template_options } = action.payload
            return Object.assign({}, sealing_petition_template_options)
        }
    }
})

// NB - not exporting any actions from here, because 
// the only action that edits this part of state is
// the FETCH_USER_PROFILE_SUCCEEDED part.
export default combineReducers({
    expungementTemplates: expungementTemplateSlice.reducer,
    sealingTemplates: sealingTemplateSlice.reducer,})