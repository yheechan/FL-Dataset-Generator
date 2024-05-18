#include "../music_utility.h"
#include "vtwd.h"

bool VTWD::ValidateDomain(const std::set<std::string> &domain)
{
	return true;
}

bool VTWD::ValidateRange(const std::set<std::string> &range)
{
	return range.empty() || 
				 (range.size() == 1 &&
					(range.find("plusone") != range.end() || 
					range.find("minusone") != range.end()));
}

// Return True if the mutant operator can mutate this expression
bool VTWD::IsMutationTarget(clang::Expr *e, MusicContext *context)
{
	// cout<<"we are here"<<endl;
	if (!ExprIsScalarReference(e))
		return false;

	SourceLocation start_loc = e->getBeginLoc();
	SourceLocation end_loc = GetEndLocOfExpr(e, context->comp_inst_);

	Rewriter rewriter;
	rewriter.setSourceMgr(
			context->comp_inst_->getSourceManager(),
			context->comp_inst_->getLangOpts());
	StmtContext &stmt_context = context->getStmtContext();

  	for(auto l_value_arg: (*(context->getSymbolTable()->getLValueArgList()))){
		SourceLocation start_loc_l = l_value_arg->getBeginLoc();
		SourceLocation end_loc_l = GetEndLocOfExpr(l_value_arg, context->comp_inst_);
		if(start_loc_l == start_loc && end_loc_l == end_loc){
			// cout<<"wozhengdemeiyouwenti"<<endl;
			// cout<<"expr: "<<ConvertToString(e, context->comp_inst_->getLangOpts())<<endl;
			return false;
		}
	}
	string token{ConvertToString(e, context->comp_inst_->getLangOpts())};
	bool is_in_domain = domain_.empty() ? true : 
                      IsStringElementOfSet(token, domain_);

	// VTWD can mutate expr that are
	// 		- inside mutation range
	// 		- not inside enum decl
	// 		- not on lhs of assignment (a+1=a -> uncompilable)
	// 		- not inside unary increment/decrement/addressop
	return context->IsRangeInMutationRange(SourceRange(start_loc, end_loc)) &&
         !stmt_context.IsInEnumDecl() &&
        //  !stmt_context.IsEnumClassType() &&
				 !stmt_context.IsInLhsOfAssignmentRange(e) &&
				 !stmt_context.IsInAddressOpRange(e) && is_in_domain &&
				 !stmt_context.IsInUnaryIncrementDecrementRange(e) &&
				 IsMutationTarget(
				 		ConvertToString(e, context->comp_inst_->getLangOpts()), context);
}



void VTWD::Mutate(clang::Expr *e, MusicContext *context)
{
	SourceLocation start_loc = e->getBeginLoc();
	SourceLocation end_loc = GetEndLocOfExpr(e, context->comp_inst_);

	Rewriter rewriter;
	rewriter.setSourceMgr(
			context->comp_inst_->getSourceManager(),
			context->comp_inst_->getLangOpts());
	string token{ConvertToString(e, context->comp_inst_->getLangOpts())};

	bool skip_plusone = false, skip_minusone = false;
	StmtContext &stmt_context = context->getStmtContext();

	string mutated_token_lable_check_plus{
        ConvertToString(e, context->comp_inst_->getLangOpts())};
	string mutated_token_lable_check_minus{
        ConvertToString(e, context->comp_inst_->getLangOpts())};
    string orig_mutated_token_label_check{
        ConvertToString(e, context->comp_inst_->getLangOpts())};    

    if (ExprIsFloat(e)){
      ConvertConstFloatExprToFloatStringAfterTwiddle(e, context->comp_inst_, mutated_token_lable_check_plus, true);
      ConvertConstFloatExprToFloatStringAfterTwiddle(e, context->comp_inst_, mutated_token_lable_check_minus, false);
	}
    else {
	  ConvertConstIntExprToIntStringAfterTwiddle(e, context->comp_inst_, mutated_token_lable_check_plus, true);
      ConvertConstIntExprToIntStringAfterTwiddle(e, context->comp_inst_, mutated_token_lable_check_minus, false);
	}

	// cout << "orig mutated: " << orig_mutated_token_label_check << endl;
    // cout << "converted mutated_minus: " << mutated_token_lable_check_minus << endl;
	// cout << "converted mutated_plus: " << mutated_token_lable_check_plus << endl;

	if (stmt_context.IsInSwitchCaseRange(e) &&
    IsDuplicateCaseLabel(mutated_token_lable_check_plus, context->switchstmt_info_list_)){
    //   cout<<"jiabuxing"<<endl;
	  skip_plusone = true;
    }
	if (stmt_context.IsInSwitchCaseRange(e) &&
    IsDuplicateCaseLabel(mutated_token_lable_check_minus, context->switchstmt_info_list_)){
    //   cout<<"jianbuxing"<<endl;
	  skip_minusone = true;
    }

	

	auto Canonicaltype = (e->getType()).getCanonicalType();

	if ((range_.empty() || 
			(!range_.empty() && range_.find("plusone") != range_.end())) && !skip_plusone)
	{
		if(ExprIsEnumClass(e)){
			token = "static_cast<int>(" + token + ")";
		}
		string mutated_token = "(" + token + "+1)";
		if(ExprIsEnum(e)){
			string type_ = e->getType().getDesugaredType(context->comp_inst_->getASTContext()).getAsString();
			_BoolTobool(type_);
			StaticCastToType(mutated_token,type_);
		}
		if(const auto *BT = dyn_cast<BuiltinType>(Canonicaltype) ){
			if(BT->getKind() != BuiltinType::Int){
				string type_ = e->getType().getDesugaredType(context->comp_inst_->getASTContext()).getAsString();
				_BoolTobool(type_);
				StaticCastToType(mutated_token,type_);		
			}
		}

		context->mutant_database_.AddMutantEntry(context->getStmtContext(),
				name_, start_loc, end_loc, token, mutated_token, 
				context->getStmtContext().getProteumStyleLineNum(), "plus");
	}

	if ((range_.empty() || 
			(!range_.empty() && range_.find("minusone") != range_.end())) && !skip_minusone)
	{
		if(ExprIsEnumClass(e)){
			token = "static_cast<int>(" + token + ")";
		}
		string mutated_token = "(" + token + "-1)";
		if(ExprIsEnum(e)){
			string type_ = e->getType().getDesugaredType(context->comp_inst_->getASTContext()).getAsString();
			_BoolTobool(type_);
			StaticCastToType(mutated_token,type_);
		}
		if(const auto *BT = dyn_cast<BuiltinType>(Canonicaltype) ){
			if(BT->getKind() != BuiltinType::Int){
				string type_ = e->getType().getDesugaredType(context->comp_inst_->getASTContext()).getAsString();
				_BoolTobool(type_);
				StaticCastToType(mutated_token,type_);		
			}
		}

		context->mutant_database_.AddMutantEntry(context->getStmtContext(),
				name_, start_loc, end_loc, token, mutated_token, 
				context->getStmtContext().getProteumStyleLineNum(), "minus");
	}
}



bool VTWD::IsMutationTarget(std::string scalarref_name, MusicContext *context)
{
	// if reference name is in the nonMutatableList then it is not mutatable
	ScalarReferenceNameList *scalarref_list = \
			context->non_VTWD_mutatable_scalarref_list_;

  for (auto it = (*scalarref_list).begin(); it != (*scalarref_list).end(); ++it)
    if (scalarref_name.compare(*it) == 0)
    {
    	scalarref_list->erase(it);
      return false;
    }

  return true;
}

bool VTWD::IsDuplicateCaseLabel(
		string new_label, SwitchStmtInfoList *switchstmt_list)
{
  for (auto case_value: (*switchstmt_list).back().second){
    // cout<<"########"<<endl;
    // cout<<"label that need to check: "<<new_label<<" compare with "<<case_value<<endl;
    // cout<<"########"<<endl;
    if (new_label.compare(case_value) == 0)
	    return true;
  }

	return false;
}