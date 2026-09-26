from restore_boundary_and import restore_boundary_and

def test_rendering_only():
    for label in ['pass','fail','uncertain']:
        value={'claims':[{'text':'A','label':label},{'text':'B.','label':label}]}
        result,edits=restore_boundary_and('A, and B.',value)
        assert result['claims'][1]=={'text':'and B.','label':label}
        assert len(edits)==1 and value['claims'][1]['text']=='B.'

def test_substantive_gaps_not_repaired():
    for gap in ['not ', 'or ', 'but ', 'and not ', 'and only if ', 'candy ']:
        result,edits=restore_boundary_and('A, '+gap+'B.',{'claims':[{'text':'A'},{'text':'B.'}]})
        assert not edits
