#include "../music_utility.h"
#include "orln.h"

extern set<string> relational_operators;
extern set<string> logical_operators;

bool ORLN::ValidateDomain(const std::set<std::string> &domain)
{
	for (auto it: domain)
  	if (relational_operators.find(it) == relational_operators.end())
    	// cannot find input domain inside valid domain
      return false;

  return true;
}

bool ORLN::ValidateRange(const std::set<std::string> &range)
{
	for (auto it: range)
  	if (logical_operators.find(it) == logical_operators.end())
    	// cannot find input range inside valid range
      return false;

  return true;
}

void ORLN::setDomain(std::set<std::string> &domain)
{
	if (domain.empty())
		domain_ = relational_operators;
	else
		domain_ = domain;
}

void ORLN::setRange(std::set<std::string> &range)
{
	if (range.empty())
		range_ = logical_operators;
	else
		range_ = range;
}

bool ORLN::IsMutationTarget(clang::Expr *e, MusicContext *context)
{
	if (BinaryOperator *bo = dyn_cast<BinaryOperator>(e))
	{
		string binary_operator{bo->getOpcodeStr()};
		SourceLocation start_loc = bo->getOperatorLoc();
		SourceManager &src_mgr = context->comp_inst_->getSourceManager();
		// cout << "cp orln\n";
		SourceLocation end_loc = src_mgr.translateLineCol(
				src_mgr.getMainFileID(),
				GetLineNumber(src_mgr, start_loc),
				GetColumnNumber(src_mgr, start_loc) + binary_operator.length());
		StmtContext &stmt_context = context->getStmtContext();

		// Return True if expr is in mutation range, NOT inside array decl size
		// and NOT inside enum declaration.
		if (context->IsRangeInMutationRange(SourceRange(start_loc, end_loc)) &&
				!stmt_context.IsInArrayDeclSize() &&
				!stmt_context.IsInEnumDecl() &&
				// !stmt_context.IsEnumClassType() &&
				domain_.find(binary_operator) != domain_.end())
			return true;
	}

	return false;
}



void ORLN::Mutate(clang::Expr *e, MusicContext *context)
{
	BinaryOperator *bo;
	if (!(bo = dyn_cast<BinaryOperator>(e)))
		return;

	string token{bo->getOpcodeStr()};
	string typestring{"bool"};
	string rhs_token, lhs_token;


	bool modify_lhs = false;
	bool modify_rhs = false;

	SourceLocation start_loc = bo->getOperatorLoc();
	SourceManager &src_mgr = context->comp_inst_->getSourceManager();
	// cout << "cp orln\n";
	SourceLocation end_loc = src_mgr.translateLineCol(
			src_mgr.getMainFileID(),
			GetLineNumber(src_mgr, start_loc),
			GetColumnNumber(src_mgr, start_loc) + token.length());

	Expr* lhs = bo->getLHS();
	Expr* rhs = bo->getRHS();
	auto Canonicaltype_l = (lhs->getType()).getCanonicalType();
	auto Canonicaltype_r = (rhs->getType()).getCanonicalType();

	string Canonicaltype_l_string = (lhs->getType()).getCanonicalType().getAsString(context->comp_inst_->getASTContext().getPrintingPolicy());
	string Canonicaltype_r_string = (rhs->getType()).getCanonicalType().getAsString(context->comp_inst_->getASTContext().getPrintingPolicy());
	string type_str_l {(lhs->getType()).getAsString()};
	string type_str_r {(rhs->getType()).getAsString()};
	// cout<<"lhs: "<<ConvertToString(lhs, context->comp_inst_->getLangOpts())<<" type: "<<Canonicaltype_l_string<<" check: "<<(Canonicaltype_l.getTypePtr()->isDependentType())<<" typestring: "<<(lhs->getType()).getAsString()<<endl;
	// cout<<"rhs: "<<ConvertToString(rhs, context->comp_inst_->getLangOpts())<<" type: "<<Canonicaltype_r_string<<" check: "<<(Canonicaltype_r.getTypePtr()->isDependentType())<<endl;
	for (char& c : type_str_l) {
        c = std::tolower(c);
    }
	for (char& j : type_str_r) {
        j = std::tolower(j);
    }
	if(type_str_l.find("iterator") != string::npos)
		return;
	if(type_str_r.find("iterator") != string::npos)
		return;

	if(ExprIsEnumClass(lhs) || Canonicaltype_l.getTypePtr()->isDependentType()){
		modify_lhs = true;
		lhs_token = ConvertToString(lhs, context->comp_inst_->getLangOpts());
		StaticCastToType(lhs_token,typestring);
		start_loc = lhs->getBeginLoc();
	}
	if(const auto *BT = dyn_cast<BuiltinType>(Canonicaltype_l) ){
      if(BT->getKind() != BuiltinType::Bool){
		// cout<<"meiwentia"<<endl;
        modify_rhs = true;
		rhs_token = ConvertToString(rhs, context->comp_inst_->getLangOpts());
		SourceLocation start_of_rhs = rhs->getBeginLoc();
		end_loc = start_of_rhs.getLocWithOffset(rhs_token.length());
		StaticCastToType(rhs_token,typestring);
      }
    }

	if(ExprIsEnumClass(rhs)|| Canonicaltype_r.getTypePtr()->isDependentType()){
		modify_rhs = true;
		rhs_token = ConvertToString(rhs, context->comp_inst_->getLangOpts());
		SourceLocation start_of_rhs = rhs->getBeginLoc();
		end_loc = start_of_rhs.getLocWithOffset(rhs_token.length());
		StaticCastToType(rhs_token,typestring);
	}
	if(const auto *BT = dyn_cast<BuiltinType>(Canonicaltype_r) ){
      if(BT->getKind() != BuiltinType::Bool){
        modify_rhs = true;
		rhs_token = ConvertToString(rhs, context->comp_inst_->getLangOpts());
		SourceLocation start_of_rhs = rhs->getBeginLoc();
		end_loc = start_of_rhs.getLocWithOffset(rhs_token.length());
		StaticCastToType(rhs_token,typestring);
      }
    }

	for (auto mutated_token: range_)
		if (token.compare(mutated_token) != 0)
		{
			if(modify_rhs)
				mutated_token.append(rhs_token);
			if(modify_lhs)
				mutated_token.insert(0, lhs_token);
			// cout<<"mutated :"<<mutated_token<<endl;
			context->mutant_database_.AddMutantEntry(context->getStmtContext(),
					name_, start_loc, end_loc, token, mutated_token, 
					context->getStmtContext().getProteumStyleLineNum(), token+mutated_token);
		}
}

